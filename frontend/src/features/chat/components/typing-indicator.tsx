"use client";

import { BarChart2 } from 'lucide-react';

interface TypingIndicatorProps {
  stage?: string | null;
}

export function TypingIndicator({ stage }: TypingIndicatorProps) {
  return (
    <div className="flex items-start gap-3">
      {/* Bot avatar */}
      <div className="w-8 h-8 rounded-full bg-[#FF441F] flex items-center justify-center flex-shrink-0">
        <BarChart2 size={14} color="white" />
      </div>

      <div className="flex flex-col gap-1">
        {/* Dots bubble */}
        <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
          <div className="flex items-center gap-1.5">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-gray-400"
                style={{
                  animation: `typing-bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                }}
              />
            ))}
          </div>
        </div>

        {/* Stage text */}
        {stage && (
          <span className="text-xs text-gray-400 ml-1">{stage}</span>
        )}

        <style jsx>{`
          @keyframes typing-bounce {
            0%, 60%, 100% {
              opacity: 0.4;
              transform: translateY(0);
            }
            30% {
              opacity: 1;
              transform: translateY(-3px);
            }
          }
        `}</style>
      </div>
    </div>
  );
}
