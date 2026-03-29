"use client";
import { create } from 'zustand';
import type { InsightReport, InsightProgress } from '@/types/api';
import { API_BASE_URL } from '@/lib/api';

export type SidebarTab = 'chat' | 'insights';

interface InsightsState {
  sidebarTab: SidebarTab;
  report: InsightReport | null;
  isGenerating: boolean;
  progress: InsightProgress | null;
  activeSection: string;
  error: string | null;

  setSidebarTab: (tab: SidebarTab) => void;
  setActiveSection: (section: string) => void;
  fetchCachedReport: () => Promise<void>;
  generateReport: () => Promise<void>;
}

export const useInsightsStore = create<InsightsState>((set) => ({
  sidebarTab: 'chat',
  report: null,
  isGenerating: false,
  progress: null,
  activeSection: 'resumen',
  error: null,

  setSidebarTab: (tab) => set({ sidebarTab: tab }),
  setActiveSection: (section) => set({ activeSection: section }),

  fetchCachedReport: async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/insights/report`);
      const data = await res.json();
      if (data.report) {
        set({ report: data.report });
      }
    } catch {
      // No cached report, that's fine
    }
  },

  generateReport: async () => {
    set({ isGenerating: true, progress: null, error: null });

    try {
      const res = await fetch(`${API_BASE_URL}/insights/generate`, {
        method: 'POST',
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader = res.body?.getReader();
      if (!reader) throw new Error('No readable stream');

      const decoder = new TextDecoder();
      let buffer = '';

      // Use same line-by-line SSE parsing pattern as the chat stream
      // (proven to work with sse-starlette's \r\n line endings)
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEventType = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEventType = line.slice(6).trim();
            continue;
          }

          if (!line.startsWith('data:')) continue;
          const raw = line.slice(5).trim();
          if (!raw) continue;

          let data: Record<string, unknown>;
          try { data = JSON.parse(raw); } catch { continue; }

          const eventType = currentEventType;
          currentEventType = '';

          if (eventType === 'progress') {
            set({ progress: data as unknown as InsightProgress });
          } else if (eventType === 'report') {
            set({ report: data as unknown as InsightReport });
          }
        }
      }
    } catch (err) {
      set({ error: (err as Error).message });
    } finally {
      set({ isGenerating: false });
    }
  },
}));
