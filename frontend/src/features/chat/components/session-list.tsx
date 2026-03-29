"use client";

import { MessageSquare } from 'lucide-react';
import { useSessionStore } from '@/stores/session-store';

export function SessionList() {
  const { sessions, activeSessionId, setActiveSession } = useSessionStore();

  if (sessions.length === 0) {
    return (
      <p className="text-xs text-gray-400 px-3 py-2">No hay sesiones previas</p>
    );
  }

  return (
    <div className="space-y-1">
      {sessions.map((session) => {
        const isActive = session.id === activeSessionId;
        return (
          <button
            key={session.id}
            onClick={() => setActiveSession(session.id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left transition-colors ${
              isActive
                ? 'bg-orange-50 border border-orange-200'
                : 'hover:bg-gray-50 border border-transparent'
            }`}
          >
            <MessageSquare
              size={13}
              className={isActive ? 'text-[#FF441F]' : 'text-gray-400'}
            />
            <span
              className={`text-sm truncate ${
                isActive ? 'text-[#FF441F] font-medium' : 'text-gray-700'
              }`}
            >
              {session.name}
            </span>
          </button>
        );
      })}
    </div>
  );
}
