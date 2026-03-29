"use client";

import { useState, useRef, useEffect } from 'react';
import { Plus, Clock, Lightbulb, MessageSquare, X, Trash2, MoreHorizontal } from 'lucide-react';
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
  const diffMins = Math.floor(Math.abs(diffMs) / 60000);
  if (diffMins < 1) return 'Ahora';
  if (diffMins < 60) return `Hace ${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `Hace ${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  return `Hace ${diffDays}d`;
}

function SessionItem({
  session,
  isActive,
  onSelect,
  onDelete,
}: {
  session: Session;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [menuOpen]);

  return (
    <div className="group relative">
      <button
        onClick={onSelect}
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
            className={`text-sm truncate pr-6 ${
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

      {/* Three-dot menu trigger */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setMenuOpen((prev) => !prev);
        }}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-all"
      >
        <MoreHorizontal size={14} />
      </button>

      {/* Dropdown menu */}
      {menuOpen && (
        <div
          ref={menuRef}
          className="absolute right-1 top-full mt-1 z-50 bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[140px]"
        >
          <button
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen(false);
              onDelete();
            }}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            <Trash2 size={13} />
            Eliminar
          </button>
        </div>
      )}
    </div>
  );
}

export function Sidebar({
  isOpen,
  onClose,
  onNewSession,
  onSelectSuggestion,
  suggestions = [],
}: SidebarProps) {
  const { sessions, activeSessionId, setActiveSession, loadSessionMessages, deleteSession, sessionsLoading } = useSessionStore();

  const handleSessionClick = (session: Session) => {
    setActiveSession(session.id);
    loadSessionMessages(session.id);
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
                  {sessionsLoading ? (
                    <>
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="flex items-center gap-2.5 px-3 py-2 animate-pulse">
                          <div className="w-3.5 h-3.5 bg-gray-200 rounded" />
                          <div className="flex-1 space-y-1.5">
                            <div className="h-3.5 bg-gray-200 rounded w-3/4" />
                            <div className="h-2.5 bg-gray-100 rounded w-1/2" />
                          </div>
                        </div>
                      ))}
                    </>
                  ) : sessions.length === 0 ? (
                    <p className="text-xs text-gray-400 px-3 py-2">
                      No hay sesiones previas
                    </p>
                  ) : (
                    sessions.map((session) => (
                      <SessionItem
                        key={session.id}
                        session={session}
                        isActive={session.id === activeSessionId}
                        onSelect={() => handleSessionClick(session)}
                        onDelete={() => deleteSession(session.id)}
                      />
                    ))
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
