import { create } from 'zustand';
import type { Session, ProactiveSuggestion } from '@/types/api';
import { apiFetch } from '@/lib/api';

interface DataFreshness {
  last_updated: string;
  tables: Record<string, number>;
}

interface SessionState {
  activeSessionId: string | null;
  sessions: Session[];
  sessionsLoading: boolean;
  suggestions: ProactiveSuggestion[];
  dataFreshness: DataFreshness | null;
  setActiveSession: (id: string) => void;
  addSession: (session: Session) => void;
  updateSession: (id: string, updates: Partial<Session>) => void;
  fetchSessions: () => Promise<void>;
  fetchSuggestions: () => Promise<void>;
  fetchDataFreshness: () => Promise<void>;
}

export const useSessionStore = create<SessionState>((set) => ({
  activeSessionId: null,
  sessions: [],
  sessionsLoading: false,
  suggestions: [],
  dataFreshness: null,

  setActiveSession: (id) =>
    set({ activeSessionId: id }),

  addSession: (session) =>
    set((state) => ({
      sessions: [session, ...state.sessions],
      activeSessionId: session.id,
    })),

  updateSession: (id, updates) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === id ? { ...s, ...updates } : s
      ),
    })),

  fetchSessions: async () => {
    set({ sessionsLoading: true });
    try {
      const data = await apiFetch<{ sessions: Array<{ session_id: string; title: string; created_at: string; message_count: number }> }>('/chat/sessions');
      const sessions: Session[] = data.sessions.map((s) => ({
        id: s.session_id,
        name: s.title || `Sesion ${s.session_id.slice(0, 8)}`,
        timestamp: new Date(s.created_at),
        messages: [],
        preview: `${s.message_count} mensajes`,
      }));
      set({ sessions, sessionsLoading: false });
    } catch {
      set({ sessionsLoading: false });
    }
  },

  fetchSuggestions: async () => {
    try {
      const suggestions = await apiFetch<ProactiveSuggestion[]>('/chat/suggestions');
      set({ suggestions });
    } catch {
      // API not available, keep empty suggestions
    }
  },

  fetchDataFreshness: async () => {
    try {
      const data = await apiFetch<DataFreshness>('/chat/data-freshness');
      set({ dataFreshness: data });
    } catch {
      // API not available
    }
  },
}));
