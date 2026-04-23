from __future__ import annotations

import base64
import json
import mimetypes
from io import BytesIO
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request
from uuid import uuid4

from ..config import EndpointConfig
from ..contracts import BlockCandidate, GenerationMetadata
from ..exceptions import EndpointConfigurationError, TranscriptionError
from .block_runner import BlockTranscriber, TranscriptionRequest


class OpenAICompatibleBlockTranscriber(BlockTranscriber):
    """Endpoint-backed block transcriber for OpenAI-compatible vision chat APIs."""

    def __init__(self, endpoint: EndpointConfig):
        self.endpoint = endpoint
        self._validate_endpoint()

    def generate_candidates(self, request: TranscriptionRequest) -> list[BlockCandidate]:
        candidates: list[BlockCandidate] = []
        for idx in range(request.num_candidates):
            payload = self._build_payload(request)
            response_json = self._post_json(payload)
            candidate = self._candidate_from_response(request, response_json, candidate_index=idx)
            candidates.append(candidate)
        return candidates

    def _build_payload(self, request: TranscriptionRequest) -> dict[str, object]:
        image_url = self._build_data_url(request)
        return {
            "model": self.endpoint.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": request.prompt_text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            "max_tokens": self.endpoint.max_tokens,
            "temperature": self.endpoint.temperature,
        }

    def _post_json(self, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            **self.endpoint.extra_headers,
        }
        api_key = self.endpoint.resolved_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib_request.Request(
            self.endpoint.chat_completions_url(),
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self.endpoint.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TranscriptionError(
                f"Endpoint returned HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except urllib_error.URLError as exc:
            raise TranscriptionError(f"Endpoint request failed: {exc}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TranscriptionError(f"Endpoint returned invalid JSON: {raw[:500]}") from exc

    def _candidate_from_response(
        self,
        request: TranscriptionRequest,
        response_json: dict[str, object],
        *,
        candidate_index: int,
    ) -> BlockCandidate:
        choices = response_json.get("choices")
        if not isinstance(choices, list) or not choices:
            raise TranscriptionError(f"Endpoint response missing choices: {response_json}")
        choice = choices[0]
        if not isinstance(choice, dict):
            raise TranscriptionError(f"Endpoint choice had unexpected shape: {choice}")

        finish_reason = str(choice.get("finish_reason") or "")
        message = choice.get("message")
        if not isinstance(message, dict):
            raise TranscriptionError(f"Endpoint response missing message payload: {response_json}")
        content = self._extract_text_content(message.get("content"))
        syntax_valid = bool(content.strip()) and finish_reason in {"stop", "end_turn", ""}

        return BlockCandidate(
            page_id=request.page.page_id,
            block_id=request.block.block_id,
            candidate_id=f"{request.block.block_id}_{uuid4().hex[:8]}_{candidate_index}",
            block_type=request.block.block_type,
            prompt_type=request.prompt_type,
            content=content,
            raw_model_output=content,
            syntax_valid=syntax_valid,
            generation_metadata=GenerationMetadata(
                model=self.endpoint.model_name,
                prompt_type=request.prompt_type,
                temperature=self.endpoint.temperature,
                max_tokens=self.endpoint.max_tokens,
                extra={
                    "finish_reason": finish_reason,
                    "usage": response_json.get("usage"),
                    "response_id": response_json.get("id"),
                    "crop_used": bool(request.crop),
                    "repair": bool(request.repair_context),
                },
            ),
            is_repair=bool(request.repair_context),
        )

    def _build_data_url(self, request: TranscriptionRequest) -> str:
        image_bytes, mime_type = self._image_bytes_for_request(request)
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _image_bytes_for_request(self, request: TranscriptionRequest) -> tuple[bytes, str]:
        crop = request.crop
        source_path = Path(crop.image_path if crop is not None else request.page.image_path)
        if crop is None:
            return source_path.read_bytes(), _guess_mime_type(source_path)

        try:
            from PIL import Image
        except ImportError:
            return source_path.read_bytes(), _guess_mime_type(source_path)

        with Image.open(source_path) as image:
            left = max(0, int(crop.bbox.x0))
            top = max(0, int(crop.bbox.y0))
            right = max(left + 1, int(crop.bbox.x1))
            bottom = max(top + 1, int(crop.bbox.y1))
            region = image.crop((left, top, right, bottom))
            if crop.scale and crop.scale > 1.0:
                width = max(1, int(region.width * crop.scale))
                height = max(1, int(region.height * crop.scale))
                resampling = getattr(Image, "Resampling", Image)
                region = region.resize((width, height), resampling.LANCZOS)
            buffer = BytesIO()
            region.save(buffer, format="PNG")
            return buffer.getvalue(), "image/png"

    def _extract_text_content(self, content: object) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    texts.append(item)
                    continue
                if isinstance(item, dict):
                    if item.get("type") in {"text", "output_text"}:
                        text = item.get("text") or item.get("output_text") or ""
                        if text:
                            texts.append(str(text))
            return "\n".join(texts).strip()
        return ""

    def _validate_endpoint(self) -> None:
        if not self.endpoint.base_url:
            raise EndpointConfigurationError("Endpoint base_url is required for OpenAI-compatible transcription")
        if not self.endpoint.model_name:
            raise EndpointConfigurationError("Endpoint model_name is required for OpenAI-compatible transcription")
        if not self.endpoint.chat_completions_url():
            raise EndpointConfigurationError("Could not resolve chat completions URL for endpoint-backed transcription")


def _guess_mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "image/png"
