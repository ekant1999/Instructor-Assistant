export interface ApiPaper {
  id: number;
  title?: string | null;
  source_url?: string | null;
  created_at?: string | null;
  note_count?: number;
  pdf_path?: string | null;
  pdf_url?: string | null;
}

export interface ApiPaperSection {
  id: number;
  page_no: number;
  text?: string;
}

export interface ApiNote {
  id: number;
  paper_id?: number | null;
  title?: string | null;
  body: string;
  tags?: string[];
  created_at?: string | null;
  paper_title?: string | null;
}

export interface ApiQuestion {
  id?: number;
  set_id?: number;
  kind: string;
  text: string;
  options?: string[] | null;
  answer?: string | null;
  explanation?: string | null;
  reference?: string | null;
}

export interface ApiQuestionSetMeta {
  id: number;
  prompt?: string | null;
  created_at?: string | null;
  count?: number;
  canvas_md_path?: string | null;
}

export interface ApiQuestionSetPayload {
  question_set: ApiQuestionSetMeta;
  questions: ApiQuestion[];
}

export interface ApiQuestionGenerationPayload {
  instructions: string;
  context?: string;
  question_count?: number;
  question_types?: string[];
  provider?: string;
}

export interface ApiQuestionGenerationResult {
  questions: ApiQuestion[];
  markdown: string;
  raw_response?: string;
}

export type ApiQuestionStreamEvent =
  | { type: "chunk"; content: string }
  | { type: "complete"; questions: ApiQuestion[]; markdown: string; raw_response?: string }
  | { type: "error"; message: string };

export interface ApiQuestionContext {
  context_id: string;
  filename: string;
  characters: number;
  preview: string;
  text: string;
}

export interface ApiPaperChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ApiPaperChatResponse {
  message: string;
  paper_id: number;
  paper_title?: string | null;
  suggested_title?: string | null;
}

export interface ApiCanvasPushRequest {
  title?: string;
  course_id?: string;
  time_limit?: number;
  publish?: boolean;
  points?: Record<string, number>;
}

export interface ApiCanvasPushResult {
  quiz_id: number;
  quiz_url: string;
  quiz_title: string;
  course_id: string;
  total_questions: number;
  uploaded_questions: number;
  published: boolean;
}

export type ApiAgentRole = "user" | "assistant" | "tool";

export interface ApiAgentChatMessage {
  role: ApiAgentRole;
  content: string;
  name?: string | null;
}

export interface ApiRagIngestRequest {
  papers_dir?: string;
  paper_ids?: number[];
  index_dir?: string;
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface ApiRagIngestResponse {
  success: boolean;
  message: string;
  num_documents?: number;
  num_chunks?: number;
  index_dir?: string;
}

export interface ApiRagIndexStatusResponse {
  exists: boolean;
  message: string;
  index_dir?: string;
}

export interface ApiRagContextInfo {
  paper: string;
  source: string;
  chunk_count: number;
  index: number;
}

export interface ApiRagQueryRequest {
  question: string;
  index_dir?: string;
  k?: number;
  headless?: boolean;
}

export interface ApiRagQueryResponse {
  question: string;
  answer: string;
  context: ApiRagContextInfo[];
  num_sources: number;
}
