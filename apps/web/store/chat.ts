import { create } from 'zustand';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent?: string;
  createdAt: Date;
}

interface ChatStore {
  messages: ChatMessage[];
  isLoading: boolean;
  addMessage: (msg: Omit<ChatMessage, 'id' | 'createdAt'>) => void;
  setLoading: (loading: boolean) => void;
  clear: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  isLoading: false,
  addMessage: (msg) =>
    set(s => ({
      messages: [
        ...s.messages,
        { ...msg, id: crypto.randomUUID(), createdAt: new Date() },
      ],
    })),
  setLoading: (isLoading) => set({ isLoading }),
  clear: () => set({ messages: [] }),
}));
