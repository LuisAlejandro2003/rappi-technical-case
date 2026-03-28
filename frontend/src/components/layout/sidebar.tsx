"use client";

import { Plus, Clock, Lightbulb, MessageSquare, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionStore } from '@/stores/session-store';
import type { Session, ProactiveSuggestion } from '@/types/api';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewSession: () => void;
  onSelectSuggestion: (text: string) => void;
  suggestions?: ProactiveSuggestion[];
}

const categoryColors: Record<string, string> = {
  Alerta: 'bg-red-100 text-red-700',
  Tendencia: 'bg-blue-100 text-blue-700',
  Sugerencia: 'bg-orange-100 text-orange-700',
  Analisis: 'bg-purple-100 text-purple-700',
};

function timeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Ahora';
  if (diffMins < 60) return `Hace ${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `Hace ${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  return `Hace ${diffDays}d`;
}

export function Sidebar({
  isOpen,
  onClose,
  onNewSession,
  onSelectSuggestion,
  suggestions = [],
}: SidebarProps) {
  const { sessions, activeSessionId, setActiveSession } = useSessionStore();

  const handleSessionClick = (session: Session) => {
    setActiveSession(session.id);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop for mobile */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 z-30 lg:hidden"
            onClick={onClose}
          />

          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="fixed left-0 top-14 bottom-0 z-40 bg-white border-r border-gray-200 overflow-hidden flex flex-col"
          >
            <div className="flex-1 overflow-y-auto p-4 space-y-6" style={{ width: 260 }}>
              {/* Close button (mobile) */}
              <div className="flex justify-end lg:hidden">
                <button onClick={onClose} className="p-1 rounded-lg text-gray-400 hover:text-gray-600">
                  <X size={16} />
                </button>
              </div>

              {/* New session button */}
              <button
                onClick={onNewSession}
                className="w-full flex items-center justify-center gap-2 py-2.5 border-2 border-dashed border-gray-300 rounded-xl text-sm text-gray-500 hover:border-[#FF441F] hover:text-[#FF441F] transition-colors"
              >
                <Plus size={14} />
                Nueva sesion
              </button>

              {/* Session history */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Clock size={13} className="text-gray-400" />
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Historial
                  </span>
                </div>
                <div className="space-y-1">
                  {sessions.map((session) => {
                    const isActive = session.id === activeSessionId;
                    return (
                      <button
                        key={session.id}
                        onClick={() => handleSessionClick(session)}
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
                        <div className="flex-1 min-w-0">
                          <p
                            className={`text-sm truncate ${
                              isActive ? 'text-[#FF441F] font-medium' : 'text-gray-700'
                            }`}
                          >
                            {session.name}
                          </p>
                          <p className="text-xs text-gray-400">
                            {timeAgo(session.timestamp)}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                  {sessions.length === 0 && (
                    <p className="text-xs text-gray-400 px-3 py-2">
                      No hay sesiones previas
                    </p>
                  )}
                </div>
              </div>

              {/* Proactive suggestions */}
              {suggestions.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Lightbulb size={13} className="text-gray-400" />
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      Sugerencias
                    </span>
                  </div>
                  <div className="space-y-2">
                    {suggestions.map((suggestion) => (
                      <button
                        key={suggestion.id}
                        onClick={() => onSelectSuggestion(suggestion.text)}
                        className="w-full text-left p-3 rounded-xl border border-gray-100 hover:border-[#FF441F]/30 hover:bg-orange-50/30 transition-colors"
                      >
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium mb-1.5 ${
                            categoryColors[suggestion.category] || 'bg-gray-100 text-gray-600'
                          }`}
                        >
                          {suggestion.category}
                        </span>
                        <p className="text-xs text-gray-600 leading-relaxed">
                          {suggestion.text}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
