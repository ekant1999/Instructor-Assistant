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

export interface Paper {
  id: string;
  title: string;
  source: string;
  year: string;
  abstract?: string;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[];
  updatedAt: number;
}
