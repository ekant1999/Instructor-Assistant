export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  isLoading?: boolean;
  actions?: {
    label: string;
    type: 'link' | 'action';
    payload: string;
  }[];
}

export interface Section {
  id: string;
  title: string;
  content: string;
  selected?: boolean;
}

export interface Paper {
  id: string;
  title: string;
  source: string;
  sourceUrl?: string;
  pdfUrl?: string;
  year: string;
  authors?: string;
  abstract?: string;
  keywords?: string;
  sections?: Section[];
  metadata?: Record<string, any>;
  noteCount?: number;
  createdAt?: number;
  updatedAt?: number;
}

export interface Summary {
  id: string;
  paperId?: string;
  title: string;
  content: string;
  agent: 'Gemini' | 'GPT' | 'Qwen';
  style?: 'brief' | 'detailed' | 'teaching';
  wordCount?: number;
  isEdited?: boolean;
  editHistory?: number[];
  metadata?: Record<string, any>;
  createdAt: number;
  updatedAt: number;
}

export interface Document {
  id: string;
  type: 'summary' | 'qa_set' | 'rag_response' | 'manual';
  title: string;
  content: string;
  tags: string[];
  wordCount?: number;
  questionCount?: number;
  sourceLinks?: Array<{ type: string; id: string; title: string }>;
  paperId?: string;
  paperTitle?: string;
  agent?: string;
  metadata?: Record<string, any>;
  createdAt: number;
  updatedAt: number;
}

export interface Note extends Document {
  type: 'manual';
}

export interface Question {
  id: string;
  type: 'multiple-choice' | 'true-false' | 'short-answer' | 'essay';
  question: string;
  options?: string[]; // For multiple choice
  correctAnswer: string | number; // Answer or option index
  explanation?: string;
  difficulty?: 'easy' | 'medium' | 'hard';
}

export interface QuestionSet {
  id: string;
  title: string;
  questions: Question[];
  sourceDocumentIds?: string[];
  agent?: string;
  prompt?: string;
  metadata?: Record<string, any>;
  createdAt: number;
  updatedAt: number;
}

export interface RagQuery {
  id: string;
  query: string;
  response: string;
  agent: 'GPT Web' | 'Gemini Web' | 'Qwen Local';
  selectedDocumentIds?: string[];
  citations?: Array<{ documentId: string; documentTitle: string; page?: number; excerpt: string }>;
  settings?: Record<string, any>;
  createdAt: number;
}

export interface ContextTemplate {
  id: string;
  name: string;
  selectedDocumentIds: string[];
  createdAt: number;
  updatedAt: number;
}
