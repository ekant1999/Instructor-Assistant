import {
  ApiNote,
  ApiPaper,
  ApiPaperSection,
  ApiQuestion,
  ApiQuestionSetPayload,
  ApiSummary
} from "./api-types";
import { Document, Paper, Question, QuestionSet, Section, Summary } from "@/shared/types";

function parseTimestamp(value?: string | null): number | undefined {
  if (!value) return undefined;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return undefined;
  return parsed;
}

function sourceLabel(sourceUrl?: string | null): string {
  if (!sourceUrl) return "Unknown";
  const trimmed = sourceUrl.trim();
  if (trimmed.startsWith("10.")) return "DOI";
  if (trimmed.startsWith("http")) {
    try {
      return new URL(trimmed).hostname.replace(/^www\./, "");
    } catch {
      return "Online";
    }
  }
  return "Local";
}

function yearFromTimestamp(ts?: number): string | undefined {
  if (!ts) return undefined;
  return new Date(ts).getFullYear().toString();
}

export function mapApiPaper(api: ApiPaper): Paper {
  const createdAt = parseTimestamp(api.created_at);
  const ragUpdatedAt = parseTimestamp(api.rag_updated_at);
  return {
    id: String(api.id),
    title: api.title || "Untitled Paper",
    source: sourceLabel(api.source_url),
    sourceUrl: api.source_url || undefined,
    pdfUrl: api.pdf_url || undefined,
    year: yearFromTimestamp(createdAt) || "",
    createdAt,
    updatedAt: createdAt,
    noteCount: api.note_count,
    ragStatus: (api.rag_status || undefined) as Paper["ragStatus"],
    ragError: api.rag_error || undefined,
    ragUpdatedAt,
  };
}

export function mapApiSection(section: ApiPaperSection): Section {
  return {
    id: String(section.id),
    title: `Page ${section.page_no}`,
    content: section.text || "",
  };
}

function normalizeSummaryAgent(agent?: string | null): "Gemini" | "GPT" | "Qwen" {
  if (!agent) return "Qwen";
  const normalized = agent.toLowerCase();
  if (normalized.includes("gpt") || normalized.includes("openai")) return "GPT";
  if (normalized.includes("gemini")) return "Gemini";
  if (normalized.includes("qwen") || normalized.includes("local")) return "Qwen";
  return "Qwen";
}

function normalizeSummaryStyle(style?: string | null): Summary["style"] | undefined {
  if (!style) return undefined;
  const normalized = style.toLowerCase();
  if (normalized === "bullet" || normalized === "brief") return "brief";
  if (normalized === "detailed") return "detailed";
  if (normalized === "teaching") return "teaching";
  return undefined;
}

function inferNoteType(api: ApiNote): Document["type"] {
  const tags = (api.tags || []).map((tag) => tag.toLowerCase());
  const title = (api.title || "").toLowerCase();
  if (tags.includes("summary") || title.startsWith("summary:")) return "summary";
  if (tags.includes("qa_set") || tags.includes("question-set") || title.includes("question set")) {
    return "qa_set";
  }
  if (tags.includes("rag_response") || tags.includes("rag") || title.includes("rag")) {
    return "rag_response";
  }
  return "manual";
}

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

export function mapApiNote(api: ApiNote): Document {
  const createdAt = parseTimestamp(api.created_at) || Date.now();
  const content = api.body || "";
  return {
    id: String(api.id),
    type: inferNoteType(api),
    title: api.title || "Untitled Note",
    content,
    tags: api.tags || [],
    sourceLinks: api.paper_id
      ? [
          {
            type: "paper",
            id: String(api.paper_id),
            title: api.paper_title || "Paper",
          },
        ]
      : [],
    createdAt,
    updatedAt: createdAt,
    paperId: api.paper_id ? String(api.paper_id) : undefined,
    paperTitle: api.paper_title || undefined,
    wordCount: countWords(content),
  };
}

export function mapApiSummary(api: ApiSummary): Summary {
  const createdAt = parseTimestamp(api.created_at) || Date.now();
  const updatedAt = parseTimestamp(api.updated_at) || createdAt;
  const content = api.content || "";
  return {
    id: String(api.id),
    paperId: String(api.paper_id),
    title: api.title || "Summary",
    content,
    agent: normalizeSummaryAgent(api.agent),
    style: normalizeSummaryStyle(api.style),
    wordCount: api.word_count ?? countWords(content),
    isEdited: Boolean(api.is_edited),
    metadata: api.metadata || undefined,
    createdAt,
    updatedAt,
  };
}

const KIND_TO_TYPE: Record<string, Question["type"]> = {
  mcq: "multiple-choice",
  multiple_choice: "multiple-choice",
  multiple_choice_question: "multiple-choice",
  true_false: "true-false",
  truefalse: "true-false",
  tf: "true-false",
  short_answer: "short-answer",
  shortanswer: "short-answer",
  "short-answer": "short-answer",
  essay: "essay",
  long_answer: "essay",
};

const TYPE_TO_KIND: Record<Question["type"], string> = {
  "multiple-choice": "mcq",
  "true-false": "true_false",
  "short-answer": "short_answer",
  "essay": "essay",
};

function answerToIndex(answer: string | null | undefined, options?: string[] | null): number {
  if (!answer) return 0;
  const trimmed = answer.trim();
  if (/^[A-D]$/i.test(trimmed)) {
    return "ABCD".indexOf(trimmed.toUpperCase());
  }
  if (!options || options.length === 0) return 0;
  const idx = options.findIndex((opt) => opt.toLowerCase().trim() === trimmed.toLowerCase());
  return idx >= 0 ? idx : 0;
}

export function mapApiQuestion(api: ApiQuestion): Question {
  const type = KIND_TO_TYPE[api.kind] || "short-answer";
  const options = api.options ?? undefined;
  const correctAnswer =
    type === "multiple-choice" ? answerToIndex(api.answer, options) : api.answer || "";
  return {
    id: String(api.id ?? Math.random().toString()),
    type,
    question: api.text,
    options: options ?? undefined,
    correctAnswer,
    explanation: api.explanation ?? undefined,
  };
}

export function mapUiQuestionToApi(question: Question): ApiQuestion {
  const kind = TYPE_TO_KIND[question.type] || "short_answer";
  let answer: string | undefined;
  if (question.type === "multiple-choice") {
    if (typeof question.correctAnswer === "number") {
      answer = "ABCD"[question.correctAnswer] || "A";
    } else {
      answer = String(question.correctAnswer);
    }
  } else {
    answer = String(question.correctAnswer || "");
  }
  return {
    id: undefined,
    kind,
    text: question.question,
    options: question.options,
    answer,
    explanation: question.explanation,
  };
}

export function mapApiQuestionSet(payload: ApiQuestionSetPayload): QuestionSet {
  const createdAt = parseTimestamp(payload.question_set.created_at) || Date.now();
  const prompt = payload.question_set.prompt || "";
  return {
    id: String(payload.question_set.id),
    title: prompt ? `Q&A: ${prompt.slice(0, 60)}` : `Question Set ${payload.question_set.id}`,
    questions: payload.questions.map(mapApiQuestion),
    agent: "Qwen",
    createdAt,
    updatedAt: createdAt,
    prompt,
  };
}
