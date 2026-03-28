"use client";

import { useCallback, useRef } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { useSessionStore } from '@/stores/session-store';
import { API_BASE_URL } from '@/lib/api';
import type { Message, ResponseType, TableData, ChartData } from '@/types/api';

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

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            try {
              const event = JSON.parse(raw);

              switch (event.type) {
                case 'session':
                  if (event.session_id && !sessionId) {
                    const newSessionId: string = event.session_id;
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
                  setStatus(event.message || event.status || 'Procesando...');
                  break;

                case 'token':
                  accumulatedTextRef.current += event.content || event.token || '';
                  updateStreamingText(accumulatedTextRef.current);
                  break;

                case 'tool_call':
                  setStatus(event.message || 'Ejecutando consulta...');
                  break;

                case 'visualization':
                  if (event.visualization_type === 'table' || event.chart_type === 'table') {
                    responseType = 'table';
                    tableData = event.data as TableData;
                  } else if (event.visualization_type === 'line' || event.chart_type === 'line') {
                    responseType = 'line-chart';
                    chartData = event.data as ChartData;
                  } else if (event.visualization_type === 'bar' || event.chart_type === 'bar') {
                    responseType = 'bar-chart';
                    chartData = event.data as ChartData;
                  }
                  break;

                case 'done':
                  // Final content may come in the done event
                  if (event.content) {
                    accumulatedTextRef.current = event.content;
                  }
                  break;

                case 'error':
                  responseType = 'error';
                  accumulatedTextRef.current = event.message || 'Error procesando la solicitud';
                  break;
              }
            } catch {
              // Skip unparseable lines
            }
          }
        }

        // Add bot message with final content
        const botMessage: Message = {
          id: generateId(),
          type: 'bot',
          content: accumulatedTextRef.current || 'Respuesta recibida.',
          timestamp: new Date(),
          responseType,
          tableData,
          chartData,
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
