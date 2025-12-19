import { create } from 'zustand';
import { Message } from '@/shared/types';

// Simple ID generator to avoid external dependency for mockup
const generateId = () => Math.random().toString(36).substring(2, 9);

interface ChatState {
  messages: Message[];
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
  isStreaming: false,
  status: null,
  input: '',
  setInput: (input) => set({ input }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  clearChat: () => set({ messages: [] }),
  sendMessage: async (content) => {
    const { addMessage } = get();
    
    // Add user message
    const userMsg: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: Date.now()
    };
    addMessage(userMsg);
    set({ input: '', isStreaming: true });

    // Simulate thinking/status
    const statuses = ['Analyzing request...', 'Searching knowledge base...', 'Formulating response...'];
    
    for (const status of statuses) {
      set({ status });
      await new Promise(resolve => setTimeout(resolve, 800));
    }

    set({ status: 'Typing...' });
    
    // Simulate streaming response
    const responseId = generateId();
    let responseContent = '';
    const fullResponse = generateMockResponse(content);
    
    // Initial empty message
    addMessage({
      id: responseId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isLoading: true
    });

    // Stream characters
    const chunkSize = 5;
    for (let i = 0; i < fullResponse.length; i += chunkSize) {
      responseContent += fullResponse.slice(i, i + chunkSize);
      set((state) => ({
        messages: state.messages.map(m => 
          m.id === responseId 
            ? { ...m, content: responseContent }
            : m
        )
      }));
      await new Promise(resolve => setTimeout(resolve, 30)); // Typing speed
    }

    // Finalize
    set((state) => ({
      isStreaming: false,
      status: null,
      messages: state.messages.map(m => 
        m.id === responseId 
          ? { ...m, isLoading: false }
          : m
      )
    }));
  }
}));

function generateMockResponse(input: string): string {
  const lower = input.toLowerCase();
  if (lower.includes('paper') || lower.includes('research')) {
    return "I found several relevant papers in the library. One key paper is 'Attention Is All You Need' (Vaswani et al., 2017). Would you like me to summarize it or add it to your reading list?";
  }
  if (lower.includes('note')) {
    return "I've saved that information to your notes. You can view it in the Notes Workspace. Is there anything specific you'd like to tag it with?";
  }
  if (lower.includes('question') || lower.includes('quiz')) {
    return "I can generate a question set based on that topic. How many questions would you like? I can create multiple choice, true/false, or short answer questions.";
  }
  return "That's an interesting point. Based on your current curriculum materials, this aligns with the module on Advanced Systems. I can pull up related lecture notes if you'd like.";
}
