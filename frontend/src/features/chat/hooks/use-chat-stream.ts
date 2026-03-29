"use client";

import { useCallback, useRef } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { useSessionStore } from '@/stores/session-store';
import { API_BASE_URL } from '@/lib/api';
import type { Message, ResponseType, TableData, ChartData } from '@/types/api';
import { vizConfigToChartData, vizConfigToTableData } from '@/lib/viz-utils';

function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function useChatStream() {
  const {
    isStreaming,
    streamingText,
    currentStatus,
    addMessage,
    updateStreamingText,
    setStatus,
    setStreaming,
    clearStreaming,
  } = useChatStore();

  const { activeSessionId, addSession, setActiveSession } = useSessionStore();
  const abortRef = useRef<AbortController | null>(null);
  const accumulatedTextRef = useRef('');

  const sendMessage = useCallback(
    async (text: string) => {
      if (isStreaming) return;

      // Add user message
      const userMessage: Message = {
        id: generateId(),
        type: 'user',
        content: text,
        timestamp: new Date(),
      };
      addMessage(userMessage);

      // Start streaming
      setStreaming(true);
      setStatus('Procesando...');
      accumulatedTextRef.current = '';

      const controller = new AbortController();
      abortRef.current = controller;

      let sessionId = activeSessionId;
      let responseType: ResponseType = 'text';
      let tableData: TableData | undefined;
      let chartData: ChartData | undefined;
      let followUpSuggestions: string[] = [];

      try {
        const res = await fetch(`${API_BASE_URL}/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            message: text,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error('No readable stream');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          // SSE format: "event: <name>\ndata: <json>\n\n"
          // Track current event name across lines
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
            try {
              data = JSON.parse(raw);
            } catch {
              continue;
            }

            const eventType = currentEventType || (data.type as string) || '';
            currentEventType = ''; // reset after consuming

            switch (eventType) {
              case 'session':
                if (data.session_id && !sessionId) {
                  const newSessionId = data.session_id as string;
                  sessionId = newSessionId;
                  setActiveSession(newSessionId);
                  addSession({
                    id: newSessionId,
                    name: `Sesion ${newSessionId.slice(0, 8)}`,
                    timestamp: new Date(),
                    messages: [],
                  });
                }
                break;

              case 'status':
                setStatus((data.message as string) || 'Procesando...');
                break;

              case 'token':
                accumulatedTextRef.current += (data.text as string) || (data.content as string) || '';
                updateStreamingText(accumulatedTextRef.current);
                break;

              case 'tool_call':
                setStatus((data.tool as string) ? `Ejecutando ${data.tool}...` : 'Ejecutando consulta...');
                break;

              case 'visualization': {
                const vizType = (data.type as string) || '';
                if (vizType === 'table') {
                  responseType = 'table';
                  tableData = vizConfigToTableData(data);
                } else if (vizType === 'line') {
                  responseType = 'line-chart';
                  chartData = vizConfigToChartData(data);
                } else if (vizType === 'bar') {
                  responseType = 'bar-chart';
                  chartData = vizConfigToChartData(data);
                }
                break;
              }

              case 'follow_up_suggestions':
                followUpSuggestions = (data.suggestions as string[]) || [];
                break;

              case 'done':
                break;

              case 'error':
                responseType = 'error';
                accumulatedTextRef.current = (data.message as string) || 'Error procesando la solicitud';
                break;
            }
          }
        }

        // Add bot message with final content
        const hasVisualization = responseType && responseType !== 'text' && responseType !== 'error';
        const botMessage: Message = {
          id: generateId(),
          type: 'bot',
          content: accumulatedTextRef.current || (hasVisualization ? '' : 'Respuesta recibida.'),
          timestamp: new Date(),
          responseType,
          tableData,
          chartData,
          followUpSuggestions: followUpSuggestions.length > 0 ? followUpSuggestions : undefined,
        };
        addMessage(botMessage);
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;

        // Add error message
        const errorMessage: Message = {
          id: generateId(),
          type: 'bot',
          content: (err as Error).message || 'Error de conexion con el servidor',
          timestamp: new Date(),
          responseType: 'error',
        };
        addMessage(errorMessage);
      } finally {
        clearStreaming();
        abortRef.current = null;
      }
    },
    [isStreaming, activeSessionId, addMessage, updateStreamingText, setStatus, setStreaming, clearStreaming, addSession, setActiveSession]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    clearStreaming();
  }, [clearStreaming]);

  return {
    sendMessage,
    cancelStream,
    isStreaming,
    streamingText,
    currentStatus,
  };
}
