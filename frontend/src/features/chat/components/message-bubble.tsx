"use client";

import { BarChart2, AlertCircle, RotateCcw } from 'lucide-react';
import { motion } from 'motion/react';
import type { Message } from '@/types/api';
import { DynamicChart } from '@/features/visualization/components/dynamic-chart';

function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString('es-CO', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface UserMessageProps {
  message: Message;
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex justify-end"
    >
      <div className="max-w-[75%] flex flex-col items-end">
        <div className="bg-[#FF441F] text-white px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-relaxed shadow-sm">
          {message.content}
        </div>
        <span className="text-xs text-gray-400 mt-1 mr-1">
          {formatTime(message.timestamp)}
        </span>
      </div>
    </motion.div>
  );
}

interface BotMessageProps {
  message: Message;
  onRetry?: (content: string) => void;
}

export function BotMessage({ message, onRetry }: BotMessageProps) {
  const isError = message.responseType === 'error';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex items-start gap-3"
    >
      {/* Bot avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isError ? 'bg-red-500' : 'bg-[#FF441F]'
        }`}
      >
        {isError ? (
          <AlertCircle size={14} color="white" />
        ) : (
          <BarChart2 size={14} color="white" />
        )}
      </div>

      <div className="max-w-[85%] flex flex-col">
        <div
          className={`px-4 py-2.5 rounded-2xl rounded-tl-sm text-sm leading-relaxed shadow-sm ${
            isError
              ? 'bg-red-50 border border-red-200 text-red-700'
              : 'bg-white border border-gray-100 text-gray-800'
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>

          {isError && onRetry && (
            <button
              onClick={() => onRetry(message.content)}
              className="flex items-center gap-1 mt-2 text-xs text-red-500 hover:text-red-700 transition-colors"
            >
              <RotateCcw size={12} />
              Reintentar
            </button>
          )}
        </div>

        {/* Visualization */}
        {message.responseType &&
          message.responseType !== 'text' &&
          message.responseType !== 'error' && (
            <DynamicChart
              responseType={message.responseType}
              tableData={message.tableData}
              chartData={message.chartData}
            />
          )}

        <span className="text-xs text-gray-400 mt-1 ml-1">
          {formatTime(message.timestamp)}
        </span>
      </div>
    </motion.div>
  );
}
