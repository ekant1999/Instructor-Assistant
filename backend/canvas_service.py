from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import requests
import re

from .schemas import CanvasPushRequest

CANVAS_KIND_MAP = {
    "mcq": ("multiple_choice_question", "mcq"),
    "multiple_choice": ("multiple_choice_question", "mcq"),
    "multiple_choice_question": ("multiple_choice_question", "mcq"),
    "true_false": ("true_false_question", "true_false"),
    "truefalse": ("true_false_question", "true_false"),
    "true_false_question": ("true_false_question", "true_false"),
    "tf": ("true_false_question", "true_false"),
    "short_answer": ("short_answer_question", "short_answer"),
    "short-answer": ("short_answer_question", "short_answer"),
    "shortanswer": ("short_answer_question", "short_answer"),
    "short_answer_question": ("short_answer_question", "short_answer"),
    "essay": ("essay_question", "essay"),
    "long_answer": ("essay_question", "essay"),
    "essay_question": ("essay_question", "essay"),
}

GROUP_LABELS = {
    "mcq": "Multiple Choice Questions",
    "true_false": "True/False Questions",
    "short_answer": "Short Answer Questions",
    "essay": "Essay Questions",
}

DEFAULT_POINTS = {
    "mcq": 3,
    "short_answer": 4,
    "true_false": 2,
    "essay": 5,
}


class CanvasPushError(RuntimeError):
    """Raised when the Canvas push fails."""


@dataclass
class CanvasConfig:
    api_url: str
    token: str
    default_course_id: Optional[str]
    default_time_limit: int
    default_publish: bool

    @property
    def api_host(self) -> str:
        base = self.api_url.rstrip("/")
        suffix = "/api/v1"
        if base.endswith(suffix):
            base = base[: -len(suffix)]
        return base


class CanvasAPI:
    def __init__(self, config: CanvasConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json",
            }
        )

    def create_quiz(self, course_id: str, title: str, time_limit: int, publish: bool) -> Dict[str, Any]:
        payload = {
            "quiz": {
                "title": title,
                "quiz_type": "assignment",
                "time_limit": max(1, time_limit),
                "shuffle_answers": True,
                "published": publish,
            }
        }
        resp = self.session.post(f"{self.config.api_url}/courses/{course_id}/quizzes", json=payload, timeout=30)
        _raise_for_canvas_error(resp, "create quiz")
        return resp.json()

    def create_question_group(
        self,
        course_id: str,
        quiz_id: int,
        name: str,
        question_count: int,
        points_per_question: int,
    ) -> Optional[int]:
        data = {
            "quiz_groups[][name]": name,
            "quiz_groups[][pick_count]": question_count,
            "quiz_groups[][question_points]": points_per_question,
        }
        resp = self.session.post(
            f"{self.config.api_url}/courses/{course_id}/quizzes/{quiz_id}/groups",
            data=data,
            timeout=30,
        )
        if resp.status_code >= 400:
            # Log warning but continue without halting the whole push
            return None
        payload = resp.json()
        groups = payload.get("quiz_groups") or []
        if not groups:
            return None
        return groups[0].get("id")

    def create_question(self, course_id: str, quiz_id: int, question_data: Dict[str, Any]) -> bool:
        resp = self.session.post(
            f"{self.config.api_url}/courses/{course_id}/quizzes/{quiz_id}/questions",
            json={"question": question_data},
            timeout=30,
        )
        if resp.status_code >= 400:
            return False
        return True


def load_canvas_config() -> CanvasConfig:
    api_url = (os.getenv("CANVAS_API_URL") or "").strip().rstrip("/")
    token = (os.getenv("CANVAS_ACCESS_TOKEN") or os.getenv("CANVAS_API_TOKEN") or "").strip()
    if not api_url:
        raise CanvasPushError("Set CANVAS_API_URL in your environment to enable Canvas exports.")
    if not token:
        raise CanvasPushError("Set CANVAS_ACCESS_TOKEN (or CANVAS_API_TOKEN) to enable Canvas exports.")
    default_course_id = (os.getenv("CANVAS_COURSE_ID") or "").strip() or None
    time_limit = int(os.getenv("CANVAS_TIME_LIMIT", "30"))
    publish_flag = os.getenv("CANVAS_PUBLISH_DEFAULT", "false").lower() in {"1", "true", "yes"}
    return CanvasConfig(
        api_url=api_url,
        token=token,
        default_course_id=default_course_id,
        default_time_limit=time_limit,
        default_publish=publish_flag,
    )


def push_question_set_to_canvas(
    set_id: int,
    payload: Dict[str, Any],
    request_options: CanvasPushRequest,
) -> Dict[str, Any]:
    config = load_canvas_config()
    question_set = payload.get("question_set") or {}
    questions = payload.get("questions") or []
    if not questions:
        raise CanvasPushError("This question set does not contain any questions yet.")

    course_id = request_options.course_id or config.default_course_id
    if not course_id:
        raise CanvasPushError("Provide a Canvas course ID or set CANVAS_COURSE_ID in your .env file.")

    title = (request_options.title or question_set.get("prompt") or f"Question Set {set_id}").strip()
    time_limit = request_options.time_limit or config.default_time_limit
    publish = request_options.publish if request_options.publish is not None else config.default_publish
    points_override = request_options.points or {}
    points_map = {**DEFAULT_POINTS, **points_override}

    converted = _build_canvas_questions(questions, points_map)
    if not converted:
        raise CanvasPushError("No compatible questions were found to upload.")

    api = CanvasAPI(config)
    quiz = api.create_quiz(course_id, title, time_limit=time_limit, publish=publish)
    quiz_id = quiz.get("id")
    if not quiz_id:
        raise CanvasPushError("Canvas did not return a quiz ID.")

    # Create groups per type to preserve scoring
    group_ids: Dict[str, Optional[int]] = {}
    for type_key in GROUP_LABELS:
        type_questions = [entry for entry in converted if entry["group_key"] == type_key]
        if not type_questions:
            continue
        group_id = api.create_question_group(
            course_id,
            quiz_id,
            GROUP_LABELS[type_key],
            question_count=len(type_questions),
            points_per_question=points_map.get(type_key, 1),
        )
        group_ids[type_key] = group_id

    successes = 0
    for idx, entry in enumerate(converted, start=1):
        question_payload = dict(entry["payload"])
        question_payload.setdefault("question_name", f"Question {idx}")
        group_id = group_ids.get(entry["group_key"])
        if group_id:
            question_payload["quiz_group_id"] = group_id
        if api.create_question(course_id, quiz_id, question_payload):
            successes += 1

    quiz_url = f"{config.api_host}/courses/{course_id}/quizzes/{quiz_id}"
    return {
        "quiz_id": quiz_id,
        "quiz_url": quiz_url,
        "quiz_title": quiz.get("title") or title,
        "course_id": course_id,
        "total_questions": len(converted),
        "uploaded_questions": successes,
        "published": publish,
    }


def _build_canvas_questions(questions: List[Dict[str, Any]], points: Dict[str, int]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for idx, question in enumerate(questions, start=1):
        canvas_type, group_key = _map_question_kind(question.get("kind"))
        if not canvas_type:
            continue
        question_text = _format_html(question.get("text") or "Untitled question")
        base_payload: Dict[str, Any] = {
            "question_type": canvas_type,
            "question_text": question_text,
            "points_possible": points.get(group_key, 1),
        }
        explanation = _compose_explanation(question.get("explanation"), question.get("reference"))
        if explanation:
            base_payload["neutral_comments"] = explanation

        if canvas_type == "multiple_choice_question":
            answers = _build_mcq_answers(question.get("options"), question.get("answer"))
            if not answers:
                continue
            base_payload["answers"] = answers
        elif canvas_type == "true_false_question":
            truthy = str(question.get("answer") or "").strip().lower()
            is_true = truthy in {"true", "t", "1", "yes"}
            base_payload["answers"] = [
                {"answer_text": "True", "weight": 100 if is_true else 0},
                {"answer_text": "False", "weight": 0 if is_true else 100},
            ]
        elif canvas_type == "short_answer_question":
            answer_text = (question.get("answer") or "").strip()
            if answer_text:
                base_payload["answers"] = [{"answer_text": answer_text}]
        # essay questions don't require answers

        base_payload["question_name"] = question_text[:60] or f"Question {idx}"
        output.append(
            {
                "payload": base_payload,
                "group_key": group_key,
            }
        )
    return output


def _map_question_kind(kind: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not kind:
        return None, None
    normalized = kind.lower().strip()
    return CANVAS_KIND_MAP.get(normalized, (None, None))


def _build_mcq_answers(options: Optional[List[str]], answer: Optional[str]) -> List[Dict[str, Any]]:
    opts = _ensure_four_options(options or [])
    if not opts:
        return []
    answer_letter = _resolve_answer_letter(answer, opts)
    answers: List[Dict[str, Any]] = []
    for idx, option in enumerate(opts):
        letter = "ABCD"[idx] if idx < 4 else None
        answers.append(
            {
                "answer_text": _format_html(option),
                "weight": 100 if letter and letter == answer_letter else 0,
            }
        )
    return answers


def _ensure_four_options(options: List[str]) -> List[str]:
    cleaned = [_clean(opt) for opt in options if _clean(opt)]
    while len(cleaned) < 4:
        cleaned.append("—")
    if len(cleaned) > 4:
        cleaned = cleaned[:4]
    return cleaned


def _resolve_answer_letter(answer: Optional[str], options: List[str]) -> Optional[str]:
    if not answer:
        return None
    value = answer.strip()
    if len(value) == 1 and value.upper() in {"A", "B", "C", "D"}:
        return value.upper()
    normalized_answer = _clean(value).lower()
    for idx, option in enumerate(options):
        if _clean(option).lower() == normalized_answer:
            return "ABCD"[idx]
    return None


def _format_html(value: str) -> str:
    if not value:
        return ""
    html = _convert_basic_markdown(value)
    return html.replace("\n", "<br />")


def _compose_explanation(explanation: Optional[str], reference: Optional[str]) -> Optional[str]:
    parts = []
    if explanation and explanation.strip():
        parts.append(_clean(explanation))
    if reference and reference.strip():
        parts.append(f"(Ref: {reference.strip()})")
    if not parts:
        return None
    return " ".join(parts)


def _clean(value: str) -> str:
    return " ".join(str(value).split()).strip()


def _convert_basic_markdown(text: str) -> str:
    from html import escape

    escaped = escape(text)
    if not escaped:
        return ""
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\\)\*(?!\*)(.+?)(?<!\\)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"`([^`]+?)`", r"<code>\1</code>", escaped)
    return escaped


def _raise_for_canvas_error(response: requests.Response, action: str) -> None:
    if response.status_code < 400:
        return
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    raise CanvasPushError(f"Failed to {action}: {detail}")
