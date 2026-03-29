import { create } from 'zustand';
import type { Message } from '@/types/api';

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamingText: string;
  currentStatus: string | null;
  addMessage: (message: Message) => void;
  updateStreamingText: (text: string) => void;
  setStatus: (status: string | null) => void;
  setStreaming: (streaming: boolean) => void;
  clearStreaming: () => void;
  setMessages: (messages: Message[]) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  streamingText: '',
  currentStatus: null,

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateStreamingText: (text) =>
    set({ streamingText: text }),

  setStatus: (status) =>
    set({ currentStatus: status }),

  setStreaming: (streaming) =>
    set({ isStreaming: streaming }),

  clearStreaming: () =>
    set({ streamingText: '', currentStatus: null, isStreaming: false }),

  setMessages: (messages) =>
    set({ messages }),
}));
