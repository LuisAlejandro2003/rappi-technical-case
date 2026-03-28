"use client";

import { useState, useCallback, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import { Sidebar } from '@/components/layout/sidebar';
import { InputBar } from '@/components/layout/input-bar';
import { MessageList } from '@/features/chat/components/message-list';
import { useChatStream } from '@/features/chat/hooks/use-chat-stream';
import { useChatStore } from '@/stores/chat-store';
import { useSessionStore } from '@/stores/session-store';
import type { ProactiveSuggestion } from '@/types/api';

function generateId(): string {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { sendMessage, isStreaming } = useChatStream();
  const { setMessages } = useChatStore();
  const { addSession, fetchSessions } = useSessionStore();

  // Fetch sessions on mount
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleSend = useCallback(
    (text: string) => {
      sendMessage(text);
    },
    [sendMessage]
  );

  const handleNewSession = useCallback(() => {
    const newSession = {
      id: generateId(),
      name: `Nueva sesion`,
      timestamp: new Date(),
      messages: [],
    };
    addSession(newSession);
    setMessages([]);
    setSidebarOpen(false);
  }, [addSession, setMessages]);

  const handleSuggestionClick = useCallback(
    (text: string) => {
      sendMessage(text);
      setSidebarOpen(false);
    },
    [sendMessage]
  );

  // Placeholder suggestions (will come from backend in Phase 6)
  const suggestions: ProactiveSuggestion[] = [];

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        onNewSession={handleNewSession}
      />

      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNewSession={handleNewSession}
          onSelectSuggestion={handleSuggestionClick}
          suggestions={suggestions}
        />

        {/* Main chat area */}
        <div
          className="flex-1 flex flex-col transition-all duration-200"
          style={{ marginLeft: sidebarOpen ? 260 : 0 }}
        >
          <MessageList onSuggestionClick={handleSuggestionClick} />
          <InputBar onSend={handleSend} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
