"use client";

import { Paperclip, Send } from 'lucide-react';
import { useState, useRef, useCallback, type KeyboardEvent } from 'react';

interface InputBarProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function InputBar({ onSend, disabled = false }: InputBarProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, []);

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [text, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const canSend = text.trim().length > 0 && !disabled;

  return (
    <div className="px-4 pb-4 pt-2">
      <div className="max-w-3xl mx-auto">
        <div className="bg-gray-50 border border-gray-200 rounded-2xl px-4 py-2.5 flex items-end gap-2 transition-all focus-within:border-[#FF441F]/50 focus-within:bg-white focus-within:shadow-sm">
          {/* Attach button (disabled) */}
          <button
            disabled
            className="p-1.5 text-gray-300 cursor-not-allowed mb-0.5"
            title="Adjuntar archivo (proximamente)"
          >
            <Paperclip size={16} />
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              adjustHeight();
            }}
            onKeyDown={handleKeyDown}
            placeholder="Escribe tu pregunta sobre metricas operacionales..."
            disabled={disabled}
            rows={1}
            className="flex-1 bg-transparent text-sm text-gray-800 placeholder:text-gray-400 resize-none outline-none min-h-[20px] max-h-[120px] py-1"
          />

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={!canSend}
            className={`flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-xl transition-all mb-0.5 ${
              canSend
                ? 'bg-[#FF441F] text-white hover:shadow-md active:scale-95'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            <Send size={14} />
          </button>
        </div>
        <p className="text-center text-[11px] text-gray-400 mt-2">
          Presiona Enter para enviar, Shift+Enter para nueva linea
        </p>
      </div>
    </div>
  );
}
