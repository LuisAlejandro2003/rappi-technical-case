"use client";

import { useChatStore } from '@/stores/chat-store';
import { useChatScroll } from '../hooks/use-chat-scroll';
import { WelcomeCard } from './welcome-card';
import { UserMessage, BotMessage } from './message-bubble';
import { TypingIndicator } from './typing-indicator';
import { BarChart2 } from 'lucide-react';
import { motion } from 'motion/react';

interface MessageListProps {
  onSuggestionClick: (text: string) => void;
}

export function MessageList({ onSuggestionClick }: MessageListProps) {
  const { messages, isStreaming, streamingText, currentStatus } = useChatStore();
  const scrollRef = useChatScroll([messages, streamingText, isStreaming]);

  return (
    <div
      ref={scrollRef}
      className="flex-1 overflow-y-auto bg-[#F8F9FA]"
    >
      <div className="max-w-3xl mx-auto px-4 py-6">
        {messages.length === 0 && !isStreaming ? (
          <WelcomeCard onSuggestionClick={onSuggestionClick} />
        ) : (
          <div className="space-y-6">
            {messages.map((msg) =>
              msg.type === 'user' ? (
                <UserMessage key={msg.id} message={msg} />
              ) : (
                <BotMessage key={msg.id} message={msg} />
              )
            )}

            {/* Streaming text preview */}
            {isStreaming && streamingText && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-3"
              >
                <div className="w-8 h-8 rounded-full bg-[#FF441F] flex items-center justify-center flex-shrink-0">
                  <BarChart2 size={14} color="white" />
                </div>
                <div className="max-w-[85%]">
                  <div className="bg-white border border-gray-100 px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed shadow-sm text-gray-800">
                    <p className="whitespace-pre-wrap">{streamingText}</p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Typing indicator */}
            {isStreaming && !streamingText && (
              <TypingIndicator stage={currentStatus} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
