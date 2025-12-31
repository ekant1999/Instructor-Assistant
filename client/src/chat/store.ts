import { create } from 'zustand';
import { Message } from '@/shared/types';
import { agentChat } from '@/lib/api';
import { ApiAgentChatMessage } from '@/lib/api-types';

// Simple ID generator to avoid external dependency for mockup
const generateId = () => Math.random().toString(36).substring(2, 9);

export interface ChatAttachment {
  id: string;
  filename: string;
  characters: number;
  preview: string;
}

interface ChatState {
  messages: Message[];
  agentMessages: ApiAgentChatMessage[];
  isStreaming: boolean;
  status: string | null;
  input: string;
  attachments: ChatAttachment[];
  setInput: (input: string) => void;
  sendMessage: (content: string) => Promise<void>;
  addAttachments: (attachments: ChatAttachment[]) => void;
  removeAttachment: (id: string) => void;
  clearAttachments: () => void;
  addMessage: (message: Message) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I'm your Instructor Assistant. I can help you research papers, organize notes, generate question sets, or answer questions using your knowledge base. How can I help you today?",
      timestamp: Date.now(),
      actions: [
        { label: 'Open Research Library', type: 'link', payload: '/library' },
        { label: 'Generate Questions', type: 'link', payload: '/questions' }
      ]
    }
  ],
  agentMessages: [],
  isStreaming: false,
  status: null,
  input: '',
  attachments: [],
  setInput: (input) => set({ input }),
  addAttachments: (attachments) =>
    set((state) => ({ attachments: [...attachments, ...state.attachments] })),
  removeAttachment: (id) =>
    set((state) => ({ attachments: state.attachments.filter((item) => item.id !== id) })),
  clearAttachments: () => set({ attachments: [] }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  clearChat: () => set({ messages: [], agentMessages: [], attachments: [] }),
  sendMessage: async (content) => {
    const { addMessage, agentMessages, attachments, clearAttachments } = get();
    const trimmed = content.trim();
    if (!trimmed && attachments.length === 0) {
      return;
    }
    const messageContent = trimmed || 'Use the attached documents.';

    const userMsg: Message = {
      id: generateId(),
      role: 'user',
      content: messageContent,
      timestamp: Date.now()
    };
    addMessage(userMsg);
    set({ input: '', isStreaming: true, status: 'Thinking...' });

    try {
      const contextIds = attachments.map((attachment) => attachment.id);
      const contexts = attachments.map((attachment) => ({
        context_id: attachment.id,
        filename: attachment.filename,
        characters: attachment.characters,
        preview: attachment.preview
      }));
      const toolMessages: ApiAgentChatMessage[] = contextIds.length
        ? [
            {
              role: 'tool',
              name: 'context_hint',
              content: JSON.stringify({ context_ids: contextIds, contexts })
            }
          ]
        : [];
      const nextAgentMessages: ApiAgentChatMessage[] = [
        ...agentMessages,
        ...toolMessages,
        { role: 'user', content: messageContent }
      ];
      const responseMessages = await agentChat(nextAgentMessages);
      const uiMessages = responseMessages
        .filter((msg) => msg.role === 'user' || msg.role === 'assistant')
        .map((msg) => ({
          id: generateId(),
          role: msg.role,
          content: msg.content,
          timestamp: Date.now()
        }));

      set({
        agentMessages: responseMessages,
        messages: [
          {
            id: 'welcome',
            role: 'assistant',
            content: "Hello! I'm your Instructor Assistant. I can help you research papers, organize notes, generate question sets, or answer questions using your knowledge base. How can I help you today?",
            timestamp: Date.now(),
            actions: [
              { label: 'Open Research Library', type: 'link', payload: '/library' },
              { label: 'Generate Questions', type: 'link', payload: '/questions' }
            ]
          },
          ...uiMessages
        ],
        isStreaming: false,
        status: null
      });
      clearAttachments();
    } catch (error) {
      addMessage({
        id: generateId(),
        role: 'assistant',
        content: error instanceof Error ? error.message : 'Failed to reach the assistant.',
        timestamp: Date.now()
      });
      set({ isStreaming: false, status: null });
    }
  }
}));
