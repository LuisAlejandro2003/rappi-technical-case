import { create } from 'zustand';
import type { Session } from '@/types/api';
import { apiFetch } from '@/lib/api';

interface SessionState {
  activeSessionId: string | null;
  sessions: Session[];
  setActiveSession: (id: string) => void;
  addSession: (session: Session) => void;
  updateSession: (id: string, updates: Partial<Session>) => void;
  fetchSessions: () => Promise<void>;
}

export const useSessionStore = create<SessionState>((set) => ({
  activeSessionId: null,
  sessions: [],

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
    try {
      const data = await apiFetch<{ sessions: Array<{ session_id: string; title: string; created_at: string; message_count: number }> }>('/chat/sessions');
      const sessions: Session[] = data.sessions.map((s) => ({
        id: s.session_id,
        name: s.title || `Sesion ${s.session_id.slice(0, 8)}`,
        timestamp: new Date(s.created_at),
        messages: [],
        preview: `${s.message_count} mensajes`,
      }));
      set({ sessions });
    } catch {
      // API not available, keep empty sessions
    }
  },
}));
