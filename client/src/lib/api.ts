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
  ApiRagQueryRequest,
  ApiRagQueryResponse,
  ApiSummary
} from "./api-types";

const DEFAULT_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || "http://localhost:8010/api";
export const API_BASE = DEFAULT_BASE.replace(/\/$/, "");

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: HeadersInit = {
    ...(options.headers || {})
  };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
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
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export async function listPapers(): Promise<ApiPaper[]> {
  const data = await request<{ papers: ApiPaper[] }>("/papers");
  return data.papers;
}

export async function listPaperSections(
  paperId: number,
  includeText: boolean = true,
  maxChars?: number
): Promise<ApiPaperSection[]> {
  const params = new URLSearchParams();
  params.set("include_text", String(includeText));
  if (typeof maxChars === "number") {
    params.set("max_chars", String(maxChars));
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

export async function chatPaper(paperId: number, messages: ApiPaperChatMessage[]): Promise<ApiPaperChatResponse> {
  return request<ApiPaperChatResponse>(`/papers/${paperId}/chat`, {
    method: "POST",
    body: JSON.stringify({ messages })
  });
}

export async function listNotes(): Promise<ApiNote[]> {
  const data = await request<{ notes: ApiNote[] }>("/notes");
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

export async function listPaperSummaries(paperId: number): Promise<ApiSummary[]> {
  const data = await request<{ summaries: ApiSummary[] }>(`/papers/${paperId}/summaries`);
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
    headers: {
      "Content-Type": "application/json"
    },
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
      headers: {
        "Content-Type": "application/json"
      },
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
