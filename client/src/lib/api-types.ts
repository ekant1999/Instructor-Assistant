export interface ApiPaper {
  id: number;
  title?: string | null;
  source_url?: string | null;
  created_at?: string | null;
  note_count?: number;
  pdf_path?: string | null;
  pdf_url?: string | null;
  rag_status?: string | null;
  rag_error?: string | null;
  rag_updated_at?: string | null;
}

export interface ApiPaperSection {
  id: number;
  page_no: number;
  text?: string;
  match_score?: number;  // Relevance score from search
  match_bbox?: { x0: number; y0: number; x1: number; y1: number };
  match_block_index?: number;
  match_text?: string;
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

export interface ApiSummary {
  id: number;
  paper_id: number;
  title?: string | null;
  content: string;
  agent?: string | null;
  style?: string | null;
  word_count?: number | null;
  is_edited?: boolean | null;
  metadata?: Record<string, any> | null;
  created_at?: string | null;
  updated_at?: string | null;
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
  paper_id?: number | null;
  paper_title?: string | null;
  kind?: string | null;
  figure_number?: number | null;
  caption?: string | null;
  image_path?: string | null;
  page_number?: number | null;
}

export interface ApiRagQueryRequest {
  question: string;
  index_dir?: string;
  k?: number;
  headless?: boolean;
  paper_ids?: number[];
  provider?: string;
  search_type?: "keyword" | "embedding" | "hybrid";
}

export interface ApiRagQueryResponse {
  question: string;
  answer: string;
  context: ApiRagContextInfo[];
  num_sources: number;
}

export interface ApiRagQnaCreateRequest {
  question: string;
  answer: string;
  sources: ApiRagContextInfo[];
  scope?: string;
  provider?: string;
}

export interface ApiRagQnaItem {
  id: number;
  paper_id: number;
  question: string;
  answer: string;
  sources: ApiRagContextInfo[];
  scope?: string | null;
  provider?: string | null;
  created_at?: string | null;
}

export type SearchType = "keyword" | "embedding" | "hybrid";

export interface ApiSearchRequest {
  query: string;
  search_type?: SearchType;
  paper_ids?: number[];
  limit?: number;
}

export interface ApiSearchResult {
  id: number;
  relevance_score?: number | null;
  result_type: "paper" | "section" | "note" | "summary";
  data: any;
}

export interface ApiSearchResponse {
  query: string;
  search_type: string;
  results: ApiSearchResult[];
  total_results: number;
}
