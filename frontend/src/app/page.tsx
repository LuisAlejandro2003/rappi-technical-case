"use client";

import { useState, useCallback, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import { Sidebar } from '@/components/layout/sidebar';
import { InputBar } from '@/components/layout/input-bar';
import { MessageList } from '@/features/chat/components/message-list';
import { InsightsView } from '@/features/insights/components/insights-view';
import { useChatStream } from '@/features/chat/hooks/use-chat-stream';
import { useChatStore } from '@/stores/chat-store';
import { useSessionStore } from '@/stores/session-store';
import { useInsightsStore } from '@/stores/insights-store';


function generateId(): string {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [prefillText, setPrefillText] = useState('');
  const { sendMessage, isStreaming } = useChatStream();
  const { setMessages } = useChatStore();
  const { addSession, fetchSessions, fetchSuggestions, fetchDataFreshness, restoreActiveSession, suggestions, dataFreshness } = useSessionStore();
  const { sidebarTab, setSidebarTab } = useInsightsStore();

  // Fetch sessions, suggestions and data freshness on mount
  useEffect(() => {
    fetchSessions().then(() => {
      // After sessions are loaded, restore the previously active session
      restoreActiveSession();
    });
    fetchSuggestions();
    fetchDataFreshness();
  }, [fetchSessions, fetchSuggestions, fetchDataFreshness, restoreActiveSession]);

  const handleSend = useCallback(
    (text: string) => {
      setPrefillText('');
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
    addSession(newSession); // also persists to localStorage
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

  const handleExploreInChat = useCallback(
    (query: string) => {
      // Switch to chat tab
      setSidebarTab('chat');
      // Prefill the input bar (do NOT auto-send)
      setPrefillText(query);
    },
    [setSidebarTab]
  );

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header
        onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        onNewSession={handleNewSession}
        dataFreshness={dataFreshness}
      />

      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNewSession={handleNewSession}
          onSelectSuggestion={handleSuggestionClick}
          suggestions={suggestions}
        />

        {/* Main content area */}
        <div
          className="flex-1 flex flex-col transition-all duration-200"
          style={{ marginLeft: sidebarOpen ? 260 : 0 }}
        >
          {sidebarTab === 'insights' ? (
            <InsightsView onExploreInChat={handleExploreInChat} />
          ) : (
            <>
              <MessageList onSuggestionClick={handleSuggestionClick} />
              <InputBar
                onSend={handleSend}
                disabled={isStreaming}
                prefillText={prefillText}
                onPrefillConsumed={() => setPrefillText('')}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
