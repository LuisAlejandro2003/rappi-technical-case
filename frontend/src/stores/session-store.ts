import { create } from 'zustand';
import type { Session, ProactiveSuggestion, Message } from '@/types/api';
import { apiFetch } from '@/lib/api';
import type { VizConfig } from '@/lib/viz-utils';
import { vizConfigToChartData, vizConfigToTableData, vizTypeToResponseType } from '@/lib/viz-utils';

const ACTIVE_SESSION_KEY = 'rappi-active-session-id';

interface DataFreshness {
  last_updated: string;
  tables: Record<string, number>;
}

/** Backend message shape from GET /chat/sessions/:id */
interface BackendMessage {
  role: 'user' | 'assistant';
  content: string;
  sql_query?: string | null;
  visualization?: VizConfig | null;
  timestamp: string;
}

/** Map backend message to frontend Message type */
function mapBackendMessage(msg: BackendMessage, index: number): Message {
  const base: Message = {
    id: `loaded_${index}_${Date.now()}`,
    type: msg.role === 'user' ? 'user' : 'bot',
    content: msg.content,
    timestamp: new Date(msg.timestamp),
  };

  if (msg.visualization) {
    const viz = msg.visualization;
    base.responseType = vizTypeToResponseType(viz.type);

    if (viz.type === 'table') {
      base.tableData = vizConfigToTableData(viz);
    } else if (viz.type === 'line' || viz.type === 'bar') {
      base.chartData = vizConfigToChartData(viz);
    }
  }

  return base;
}

interface SessionState {
  activeSessionId: string | null;
  sessions: Session[];
  sessionsLoading: boolean;
  suggestions: ProactiveSuggestion[];
  dataFreshness: DataFreshness | null;
  setActiveSession: (id: string) => void;
  loadSessionMessages: (id: string) => Promise<void>;
  addSession: (session: Session) => void;
  updateSession: (id: string, updates: Partial<Session>) => void;
  deleteSession: (id: string) => Promise<void>;
  fetchSessions: () => Promise<void>;
  fetchSuggestions: () => Promise<void>;
  fetchDataFreshness: () => Promise<void>;
  restoreActiveSession: () => Promise<void>;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  activeSessionId: typeof window !== 'undefined'
    ? localStorage.getItem(ACTIVE_SESSION_KEY)
    : null,
  sessions: [],
  sessionsLoading: false,
  suggestions: [],
  dataFreshness: null,

  setActiveSession: (id) => {
    localStorage.setItem(ACTIVE_SESSION_KEY, id);
    set({ activeSessionId: id });
  },

  loadSessionMessages: async (id: string) => {
    try {
      const data = await apiFetch<{ id: string; messages: BackendMessage[] }>(
        `/chat/sessions/${id}`
      );
      const messages: Message[] = data.messages.map(mapBackendMessage);
      // Import chat store dynamically to avoid circular deps
      const { useChatStore } = await import('./chat-store');
      useChatStore.getState().setMessages(messages);
    } catch {
      // Session may not exist on backend yet (created locally)
    }
  },

  addSession: (session) => {
    localStorage.setItem(ACTIVE_SESSION_KEY, session.id);
    set((state) => ({
      sessions: [session, ...state.sessions],
      activeSessionId: session.id,
    }));
  },

  updateSession: (id, updates) =>
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === id ? { ...s, ...updates } : s
      ),
    })),

  deleteSession: async (id: string) => {
    await apiFetch(`/chat/sessions/${id}`, { method: 'DELETE' });
    const { activeSessionId } = get();
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
    }));
    if (activeSessionId === id) {
      localStorage.removeItem(ACTIVE_SESSION_KEY);
      set({ activeSessionId: null });
      const { useChatStore } = await import('./chat-store');
      useChatStore.getState().setMessages([]);
    }
  },

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

  restoreActiveSession: async () => {
    const storedId = localStorage.getItem(ACTIVE_SESSION_KEY);
    if (storedId) {
      const { sessions } = get();
      const exists = sessions.some((s) => s.id === storedId);
      if (exists) {
        set({ activeSessionId: storedId });
        await get().loadSessionMessages(storedId);
      } else {
        // Session no longer exists on backend, clear stored ID
        localStorage.removeItem(ACTIVE_SESSION_KEY);
        set({ activeSessionId: null });
      }
    }
  },
}));
