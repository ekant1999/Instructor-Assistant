import { create } from 'zustand';
import { Message } from '@/shared/types';
import { agentChat } from '@/lib/api';
import { ApiAgentChatMessage } from '@/lib/api-types';

// Simple ID generator to avoid external dependency for mockup
const generateId = () => Math.random().toString(36).substring(2, 9);

interface ChatState {
  messages: Message[];
  agentMessages: ApiAgentChatMessage[];
  isStreaming: boolean;
  status: string | null;
  input: string;
  setInput: (input: string) => void;
  sendMessage: (content: string) => Promise<void>;
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
  setInput: (input) => set({ input }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  clearChat: () => set({ messages: [], agentMessages: [] }),
  sendMessage: async (content) => {
    const { addMessage, agentMessages } = get();

    const userMsg: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: Date.now()
    };
    addMessage(userMsg);
    set({ input: '', isStreaming: true, status: 'Thinking...' });

    try {
      const nextAgentMessages: ApiAgentChatMessage[] = [
        ...agentMessages,
        { role: 'user', content }
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
