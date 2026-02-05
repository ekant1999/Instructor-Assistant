import {
  ApiAgentChatMessage,
  ApiCanvasPushRequest,
  ApiCanvasPushResult,
  ApiNote,
  ApiPaper,
  ApiPaperChatMessage,
  ApiPaperChatResponse,
  ApiPaperSection,
  ApiQuestion,
  ApiQuestionContext,
  ApiQuestionGenerationPayload,
  ApiQuestionGenerationResult,
  ApiQuestionSetMeta,
  ApiQuestionSetPayload,
  ApiQuestionStreamEvent,
  ApiRagIndexStatusResponse,
  ApiRagIngestRequest,
  ApiRagIngestResponse,
  ApiRagQnaCreateRequest,
  ApiRagQnaItem,
  ApiRagQueryRequest,
  ApiRagQueryResponse,
  ApiSummary,
  ApiSearchRequest,
  ApiSearchResponse,
  SearchType
} from "./api-types";

const runtimeBase =
  typeof globalThis !== "undefined" && (globalThis as any).__IA_API_BASE__
    ? String((globalThis as any).__IA_API_BASE__)
    : undefined;
const DEFAULT_BASE =
  runtimeBase ||
  (import.meta.env.VITE_API_BASE as string | undefined) ||
  "http://localhost:8010/api";
export const API_BASE = DEFAULT_BASE.replace(/\/$/, "");
const NGROK_SKIP_HEADER = "ngrok-skip-browser-warning";
const SHOULD_SKIP_NGROK_WARNING = /ngrok-free\.dev|ngrok\.io|ngrok\.app/i.test(API_BASE);
const NGROK_WARNING_PARAM = "ngrok-skip-browser-warning";

function addHeader(headers: HeadersInit, key: string, value: string): HeadersInit {
  if (headers instanceof Headers) {
    headers.set(key, value);
    return headers;
  }
  if (Array.isArray(headers)) {
    return [...headers, [key, value]];
  }
  return { ...(headers as Record<string, string>), [key]: value };
}

function applyNgrokSkipHeader(headers: HeadersInit): HeadersInit {
  if (!SHOULD_SKIP_NGROK_WARNING) return headers;
  return addHeader(headers, NGROK_SKIP_HEADER, "true");
}

export function getNgrokSkipHeaders(): HeadersInit {
  if (!SHOULD_SKIP_NGROK_WARNING) return {};
  return { [NGROK_SKIP_HEADER]: "true" };
}

export function withNgrokSkipParam(url: string): string {
  if (!SHOULD_SKIP_NGROK_WARNING) return url;
  try {
    const parsed = new URL(url);
    if (!parsed.searchParams.has(NGROK_WARNING_PARAM)) {
      parsed.searchParams.set(NGROK_WARNING_PARAM, "true");
    }
    return parsed.toString();
  } catch {
    return url;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let headers: HeadersInit = {
    ...(options.headers || {})
  };
  if (!(options.body instanceof FormData)) {
    headers = addHeader(headers, "Content-Type", "application/json");
  }
  headers = applyNgrokSkipHeader(headers);
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      const rawDetail = data?.detail ?? data;
      if (Array.isArray(rawDetail)) {
        detail = rawDetail
          .map((entry) => {
            if (typeof entry === "string") return entry;
            if (entry && typeof entry === "object") {
              return entry.msg || entry.message || JSON.stringify(entry);
            }
            return String(entry);
          })
          .join("; ");
      } else if (typeof rawDetail === "string") {
        detail = rawDetail;
      } else if (rawDetail && typeof rawDetail === "object") {
        detail = JSON.stringify(rawDetail);
      } else if (rawDetail != null) {
        detail = String(rawDetail);
      }
    } catch {
      // ignore
    }
    throw new Error(detail || "Request failed");
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export async function listPapers(searchQuery?: string, searchType?: "keyword" | "embedding" | "hybrid"): Promise<ApiPaper[]> {
  const params = new URLSearchParams();
  if (searchQuery) {
    params.set("q", searchQuery);
    if (searchType) {
      params.set("search_type", searchType);
    }
  }
  const query = params.toString() ? `?${params}` : "";
  const data = await request<{ papers: ApiPaper[] }>(`/papers${query}`);
  return data.papers;
}

export async function listPaperSections(
  paperId: number,
  includeText: boolean = true,
  maxChars?: number,
  searchQuery?: string,
  searchType?: "keyword" | "embedding" | "hybrid"
): Promise<ApiPaperSection[]> {
  const params = new URLSearchParams();
  params.set("include_text", String(includeText));
  if (typeof maxChars === "number") {
    params.set("max_chars", String(maxChars));
  }
  if (searchQuery) {
    params.set("q", searchQuery);
    if (searchType) {
      params.set("search_type", searchType);
    }
  }
  const query = params.toString() ? `?${params}` : "";
  const data = await request<{ sections: ApiPaperSection[] }>(`/papers/${paperId}/sections${query}`);
  return data.sections;
}

export async function getPaperContext(
  paperId: number,
  sectionIds?: number[],
  maxChars?: number
): Promise<string> {
  const params = new URLSearchParams();
  if (sectionIds && sectionIds.length > 0) {
    params.set("section_ids", sectionIds.join(","));
  }
  if (typeof maxChars === "number") {
    params.set("max_chars", String(maxChars));
  }
  const query = params.toString() ? `?${params}` : "";
  const data = await request<{ context: string }>(`/papers/${paperId}/context${query}`);
  return data.context;
}

export async function downloadPaper(input: { source: string; source_url?: string }): Promise<ApiPaper> {
  const data = await request<{ paper: ApiPaper }>("/papers/download", {
    method: "POST",
    body: JSON.stringify(input)
  });
  return data.paper;
}

export async function deletePaper(paperId: number): Promise<void> {
  await request<void>(`/papers/${paperId}`, { method: "DELETE" });
}

export async function chatPaper(
  paperId: number,
  messages: ApiPaperChatMessage[],
  provider?: string
): Promise<ApiPaperChatResponse> {
  return request<ApiPaperChatResponse>(`/papers/${paperId}/chat`, {
    method: "POST",
    body: JSON.stringify({ messages, provider })
  });
}

export async function listNotes(
  searchQuery?: string,
  searchType?: "keyword" | "embedding" | "hybrid",
  paperIds?: number[]
): Promise<ApiNote[]> {
  const params = new URLSearchParams();
  if (searchQuery) {
    params.set("q", searchQuery);
    if (searchType) {
      params.set("search_type", searchType);
    }
    if (paperIds && paperIds.length > 0) {
      params.set("paper_ids", paperIds.join(","));
    }
  }
  const query = params.toString() ? `?${params}` : "";
  const data = await request<{ notes: ApiNote[] }>(`/notes${query}`);
  return data.notes;
}

export async function createNote(input: {
  title?: string;
  body: string;
  paper_id?: number | null;
  tags?: string[];
}): Promise<ApiNote> {
  const data = await request<{ note: ApiNote }>("/notes", {
    method: "POST",
    body: JSON.stringify(input)
  });
  return data.note;
}

export async function updateNote(
  noteId: number,
  input: { title?: string; body?: string; paper_id?: number | null; tags?: string[] }
): Promise<ApiNote> {
  const data = await request<{ note: ApiNote }>(`/notes/${noteId}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
  return data.note;
}

export async function deleteNote(noteId: number): Promise<void> {
  await request<void>(`/notes/${noteId}`, { method: "DELETE" });
}

export async function listPaperSummaries(
  paperId: number,
  searchQuery?: string,
  searchType?: "keyword" | "embedding" | "hybrid"
): Promise<ApiSummary[]> {
  const params = new URLSearchParams();
  if (searchQuery) {
    params.set("q", searchQuery);
    if (searchType) {
      params.set("search_type", searchType);
    }
  }
  const query = params.toString() ? `?${params}` : "";
  const data = await request<{ summaries: ApiSummary[] }>(`/papers/${paperId}/summaries${query}`);
  return data.summaries;
}

export async function createPaperSummary(
  paperId: number,
  input: {
    title?: string;
    content: string;
    agent?: string;
    style?: string;
    word_count?: number;
    is_edited?: boolean;
    metadata?: Record<string, any>;
  }
): Promise<ApiSummary> {
  const data = await request<{ summary: ApiSummary }>(`/papers/${paperId}/summaries`, {
    method: "POST",
    body: JSON.stringify(input)
  });
  return data.summary;
}

export async function updateSummary(
  summaryId: number,
  input: {
    title?: string;
    content?: string;
    agent?: string;
    style?: string;
    word_count?: number;
    is_edited?: boolean;
    metadata?: Record<string, any>;
  }
): Promise<ApiSummary> {
  const data = await request<{ summary: ApiSummary }>(`/summaries/${summaryId}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
  return data.summary;
}

export async function deleteSummary(summaryId: number): Promise<void> {
  await request<void>(`/summaries/${summaryId}`, { method: "DELETE" });
}

export async function listQuestionSets(): Promise<ApiQuestionSetMeta[]> {
  const data = await request<{ question_sets: ApiQuestionSetMeta[] }>("/question-sets");
  return data.question_sets;
}

export async function getQuestionSet(setId: number): Promise<ApiQuestionSetPayload> {
  return request<ApiQuestionSetPayload>(`/question-sets/${setId}`);
}

export async function createQuestionSet(input: { prompt: string; questions: ApiQuestion[] }): Promise<ApiQuestionSetPayload> {
  return request<ApiQuestionSetPayload>("/question-sets", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function updateQuestionSet(
  setId: number,
  input: { prompt?: string; questions: ApiQuestion[] }
): Promise<ApiQuestionSetPayload> {
  return request<ApiQuestionSetPayload>(`/question-sets/${setId}`, {
    method: "PUT",
    body: JSON.stringify(input)
  });
}

export async function deleteQuestionSet(setId: number): Promise<void> {
  await request<void>(`/question-sets/${setId}`, { method: "DELETE" });
}

export async function generateQuestionSetWithLLM(
  input: ApiQuestionGenerationPayload
): Promise<ApiQuestionGenerationResult> {
  return request<ApiQuestionGenerationResult>("/question-sets/generate", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function streamQuestionGeneration(
  input: ApiQuestionGenerationPayload,
  onEvent: (event: ApiQuestionStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/question-sets/generate/stream`, {
    method: "POST",
    headers: applyNgrokSkipHeader({
      "Content-Type": "application/json"
    }),
    body: JSON.stringify(input),
    signal
  });
  if (!res.ok || !res.body) {
    const text = await res.text();
    throw new Error(text || "Failed to start generation stream");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);
      chunk
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .forEach((line) => {
          if (line.startsWith("data:")) {
            const payload = line.slice(5).trim();
            if (!payload) {
              return;
            }
            try {
              onEvent(JSON.parse(payload));
            } catch {
              // ignore malformed chunk
            }
          }
        });
    }
  }
}

export async function uploadQuestionContext(file: File): Promise<ApiQuestionContext> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/question-sets/context`, {
    method: "POST",
    headers: applyNgrokSkipHeader({}),
    body: formData
  });
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || "Failed to upload context");
  }
  return (await res.json()) as ApiQuestionContext;
}

export async function pushQuestionSetToCanvas(setId: number, input: ApiCanvasPushRequest): Promise<ApiCanvasPushResult> {
  return request<ApiCanvasPushResult>(`/question-sets/${setId}/canvas`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function agentChat(messages: ApiAgentChatMessage[]): Promise<ApiAgentChatMessage[]> {
  const data = await request<{ messages: ApiAgentChatMessage[] }>("/agent/chat", {
    method: "POST",
    body: JSON.stringify({ messages })
  });
  return data.messages;
}

export async function ragIngest(input: ApiRagIngestRequest): Promise<ApiRagIngestResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5 * 60 * 1000);
  try {
    const res = await fetch(`${API_BASE}/rag/ingest`, {
      method: "POST",
      headers: applyNgrokSkipHeader({
        "Content-Type": "application/json"
      }),
      body: JSON.stringify(input),
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = await res.json();
        detail = data.detail || JSON.stringify(data);
      } catch {
        // ignore
      }
      throw new Error(detail || "Request failed");
    }
    return (await res.json()) as ApiRagIngestResponse;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Ingestion timeout: The process is taking longer than expected. Please check the server logs.");
    }
    throw err;
  }
}

export async function ragGetStatus(indexDir?: string): Promise<ApiRagIndexStatusResponse> {
  const params = indexDir ? `?index_dir=${encodeURIComponent(indexDir)}` : "";
  return request<ApiRagIndexStatusResponse>(`/rag/status${params}`);
}

export async function ragQuery(input: ApiRagQueryRequest): Promise<ApiRagQueryResponse> {
  return request<ApiRagQueryResponse>("/rag/query", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function listPaperRagQna(paperId: number): Promise<ApiRagQnaItem[]> {
  return request<ApiRagQnaItem[]>(`/papers/${paperId}/rag-qa`);
}

export async function createPaperRagQna(
  paperId: number,
  input: ApiRagQnaCreateRequest
): Promise<ApiRagQnaItem> {
  return request<ApiRagQnaItem>(`/papers/${paperId}/rag-qa`, {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function deletePaperRagQna(paperId: number, qaId: number): Promise<void> {
  await request(`/papers/${paperId}/rag-qa/${qaId}`, {
    method: "DELETE"
  });
}

export async function clearPaperRagQna(paperId: number): Promise<void> {
  await request(`/papers/${paperId}/rag-qa`, {
    method: "DELETE"
  });
}

export async function unifiedSearch(input: ApiSearchRequest): Promise<ApiSearchResponse> {
  return request<ApiSearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify(input)
  });
}
