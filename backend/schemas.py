from __future__ import annotations

from typing import Any, Dict, List, Optional
from typing import Literal

from pydantic import BaseModel, Field


# Search Schemas
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    search_type: Literal["keyword", "embedding", "hybrid"] = Field(
        default="keyword",
        description="Search type: 'keyword' (FTS5), 'embedding' (FAISS), or 'hybrid' (both)",
    )
    paper_ids: Optional[List[int]] = Field(
        default=None,
        description="Optional list of paper IDs to filter by",
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results to return")


class SearchResult(BaseModel):
    id: int
    relevance_score: Optional[float] = None
    result_type: str  # "paper", "section", "note", "summary"
    data: Dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    search_type: str
    results: List[SearchResult]
    total_results: int


class NoteCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    body: str = Field(...)
    paper_id: Optional[int] = Field(default=None, ge=1)
    tags: Optional[List[str]] = Field(default=None)


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    body: Optional[str] = Field(default=None)
    paper_id: Optional[int] = Field(default=None, ge=1)
    tags: Optional[List[str]] = Field(default=None)


class SummaryCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    content: str = Field(..., min_length=1)
    agent: Optional[str] = Field(default=None, max_length=50)
    style: Optional[str] = Field(default=None, max_length=50)
    word_count: Optional[int] = Field(default=None, ge=0)
    is_edited: Optional[bool] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class SummaryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None, min_length=1)
    agent: Optional[str] = Field(default=None, max_length=50)
    style: Optional[str] = Field(default=None, max_length=50)
    word_count: Optional[int] = Field(default=None, ge=0)
    is_edited: Optional[bool] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class Question(BaseModel):
    id: Optional[int] = None
    kind: str = Field(default="short_answer", min_length=1)
    text: str = Field(..., min_length=1)
    options: Optional[List[str]] = None
    answer: Optional[str] = None
    explanation: Optional[str] = None
    reference: Optional[str] = None

class QuestionSetMeta(BaseModel):
    id: int
    prompt: Optional[str] = None
    created_at: Optional[str] = None
    count: Optional[int] = None
    canvas_md_path: Optional[str] = None


class QuestionSetPayload(BaseModel):
    question_set: QuestionSetMeta
    questions: List[Question]


class QuestionInsertionRequest(BaseModel):
    instructions: str = Field(..., min_length=5)
    context: Optional[str] = None
    question_count: Optional[int] = Field(default=None, ge=1, le=50)
    question_types: Optional[List[str]] = None
    provider: Optional[str] = None
    anchor_question_id: Optional[int] = Field(default=None, description="Existing question ID to anchor around.")
    position: Literal["before", "after"] = Field(default="after")


class QuestionInsertionPreviewResponse(BaseModel):
    question_set: QuestionSetMeta
    preview_questions: List[Question]
    merged_questions: List[Question]
    insert_index: int



class QuestionSetCreate(BaseModel):
    prompt: str = Field(..., min_length=3)
    questions: List[Question] = Field(..., min_length=1)


class QuestionSetUpdate(BaseModel):
    prompt: Optional[str] = Field(default=None, min_length=3)
    questions: List[Question] = Field(..., min_length=1)


class QuestionGenerationRequest(BaseModel):
    instructions: str = Field(..., min_length=5)
    context: Optional[str] = None
    question_count: Optional[int] = Field(default=None, ge=1, le=100)
    question_types: Optional[List[str]] = None
    provider: Optional[str] = Field(
        default=None,
        description="LLM provider identifier, e.g., 'openai' or 'local'."
    )
    format: Optional[str] = Field(
        default="json",
        description="Desired response format; currently only 'json' is supported."
    )


class QuestionGenerationResponse(BaseModel):
    questions: List[Question]
    markdown: str
    raw_response: Optional[str] = None


class QuestionContextUploadResponse(BaseModel):
    context_id: str
    filename: str
    characters: int
    preview: str
    text: str


class PaperRecord(BaseModel):
    id: int
    title: Optional[str] = None
    source_url: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_url: Optional[str] = None
    rag_status: Optional[str] = None
    rag_error: Optional[str] = None
    rag_updated_at: Optional[str] = None
    created_at: Optional[str] = None
    note_count: Optional[int] = None


class NoteRecord(BaseModel):
    id: int
    paper_id: Optional[int] = None
    title: Optional[str] = None
    body: str
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None


class PaperDownloadRequest(BaseModel):
    source: str = Field(..., min_length=3)
    source_url: Optional[str] = None


class PaperChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)


class PaperChatRequest(BaseModel):
    messages: List[PaperChatMessage] = Field(..., min_length=1)
    provider: str | None = None


class CanvasPushRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    course_id: Optional[str] = Field(default=None, min_length=1)
    time_limit: Optional[int] = Field(default=None, ge=1, le=600)
    publish: Optional[bool] = None
    points: Optional[Dict[str, int]] = None


class CanvasPushResponse(BaseModel):
    quiz_id: int
    quiz_url: str
    quiz_title: str
    course_id: str
    total_questions: int
    uploaded_questions: int
    published: bool


class AgentChatMessage(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str
    name: str | None = None


class AgentChatRequest(BaseModel):
    messages: List[AgentChatMessage] = Field(default_factory=list)


class AgentChatResponse(BaseModel):
    messages: List[AgentChatMessage]


class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    max_results: int | None = Field(default=5, ge=1, le=20)


class NewsRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    limit: int | None = Field(default=10, ge=1, le=25)


class ArxivSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    max_results: int | None = Field(default=5, ge=1, le=20)


class ArxivDownloadRequest(BaseModel):
    arxiv_id: str = Field(..., min_length=4)
    output_path: str | None = None


class PdfSummaryRequest(BaseModel):
    pdf_path: str = Field(..., min_length=1, description="Path to a PDF file")


class YoutubeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    max_results: int | None = Field(default=5, ge=1, le=20)


class YoutubeDownloadRequest(BaseModel):
    video_url: str = Field(..., min_length=4)
    output_path: str | None = None


# RAG schemas
class RAGIngestRequest(BaseModel):
    papers_dir: str | None = Field(default=None, description="Directory containing PDF files")
    paper_ids: List[int] | None = Field(
        default=None,
        description="Optional list of paper IDs to ingest from the library",
    )
    index_dir: str | None = Field(default=None, description="Directory to save the FAISS index")
    chunk_size: int | None = Field(default=1200, ge=100, le=5000)
    chunk_overlap: int | None = Field(default=200, ge=0, le=1000)


class RAGIngestResponse(BaseModel):
    success: bool
    message: str
    num_documents: int | None = None
    num_chunks: int | None = None
    index_dir: str | None = None


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    index_dir: str | None = Field(default=None, description="Directory containing the FAISS index")
    k: int | None = Field(default=6, ge=1, le=20, description="Number of chunks to retrieve")
    headless: bool | None = Field(default=False, description="Run browser in headless mode (False = show browser window for login)")
    paper_ids: List[int] | None = Field(
        default=None,
        description="Optional list of paper IDs to constrain retrieval to.",
    )
    provider: str | None = Field(
        default=None,
        description="LLM provider identifier, e.g., 'openai' or 'local'.",
    )
    search_type: str | None = Field(
        default="embedding",
        description="Search type: 'keyword' (FTS5), 'embedding' (FAISS), or 'hybrid' (both)",
    )


class RAGContextInfo(BaseModel):
    paper: str
    source: str
    chunk_count: int
    index: int
    paper_id: int | None = None
    paper_title: str | None = None
    kind: str | None = None
    figure_number: int | None = None
    caption: str | None = None
    image_path: str | None = None
    page_number: int | None = None


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    context: List[RAGContextInfo]
    num_sources: int


class RAGQnaCreateRequest(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    sources: List[RAGContextInfo] = Field(default_factory=list)
    scope: Optional[str] = Field(default="selected")
    provider: Optional[str] = Field(default=None)


class RAGQnaRecord(BaseModel):
    id: int
    paper_id: int
    question: str
    answer: str
    sources: List[RAGContextInfo] = Field(default_factory=list)
    scope: Optional[str] = None
    provider: Optional[str] = None
    created_at: Optional[str] = None


class RAGIndexStatusResponse(BaseModel):
    exists: bool
    message: str
    index_dir: str | None = None
