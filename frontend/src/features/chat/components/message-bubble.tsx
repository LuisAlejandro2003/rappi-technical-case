"use client";

import { BarChart2, AlertCircle, RotateCcw, ArrowRight } from 'lucide-react';
import { motion } from 'motion/react';
import type { Message } from '@/types/api';
import { DynamicChart } from '@/features/visualization/components/dynamic-chart';
import { MarkdownRenderer } from './markdown-renderer';

function generateFollowUps(message: Message): string[] {
  const followUps: string[] = [];
  const content = message.content.toLowerCase();

  // If response mentions a country, suggest exploring cities
  const countries = ['colombia', 'mexico', 'brasil', 'chile', 'peru', 'argentina', 'ecuador', 'costa rica', 'uruguay'];
  for (const country of countries) {
    if (content.includes(country)) {
      followUps.push(`Ver otras ciudades de ${country.charAt(0).toUpperCase() + country.slice(1)}`);
      break;
    }
  }

  // If response has a table, suggest chart view
  if (message.responseType === 'table') {
    followUps.push('Ver como grafico');
  }

  // If response has a chart, suggest exporting data
  if (message.responseType === 'line-chart' || message.responseType === 'bar-chart') {
    followUps.push('Exportar datos en tabla');
  }

  // Always include a generic deepening suggestion
  followUps.push('Profundizar en este analisis');

  return followUps.slice(0, 3);
}

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
  onFollowUp?: (text: string) => void;
  isLatest?: boolean;
}

export function BotMessage({ message, onRetry, onFollowUp, isLatest }: BotMessageProps) {
  const isError = message.responseType === 'error';
  const followUps = message.followUpSuggestions?.length
    ? message.followUpSuggestions
    : (!isError && isLatest && onFollowUp ? generateFollowUps(message) : []);

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
          <MarkdownRenderer content={message.content} />

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

        {/* Follow-up suggestion chips */}
        {followUps.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {followUps.map((text) => (
              <button
                key={text}
                onClick={() => onFollowUp?.(text)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border border-gray-200 text-gray-600 hover:border-[#FF441F] hover:text-[#FF441F] hover:bg-orange-50/50 transition-colors"
              >
                <ArrowRight size={10} />
                {text}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
