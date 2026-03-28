"use client";

import { BarChart2, Plus, Menu, ChevronDown, Circle } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useSessionStore } from '@/stores/session-store';
import type { Session } from '@/types/api';

interface HeaderProps {
  onToggleSidebar: () => void;
  onNewSession: () => void;
}

export function Header({ onToggleSidebar, onNewSession }: HeaderProps) {
  const { sessions, activeSessionId, setActiveSession } = useSessionStore();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectSession = (session: Session) => {
    setActiveSession(session.id);
    setDropdownOpen(false);
  };

  return (
    <header className="h-14 bg-white border-b border-gray-200 shadow-sm flex items-center justify-between px-4 flex-shrink-0">
      {/* Left: hamburger + logo */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-800 transition-colors"
        >
          <Menu size={18} />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-[#FF441F] rounded-lg flex items-center justify-center">
            <BarChart2 size={14} color="white" />
          </div>
          <span className="font-semibold text-gray-900 text-sm">
            Rappi <span className="text-[#FF441F]">Analytics</span>
          </span>
        </div>
      </div>

      {/* Center: session selector */}
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-sm"
        >
          <Circle size={6} className="text-green-500 fill-green-500" />
          <span className="text-gray-700 max-w-[180px] truncate">
            {activeSession?.name || 'Nueva sesion'}
          </span>
          <ChevronDown size={14} className="text-gray-400" />
        </button>

        {dropdownOpen && (
          <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 w-64 bg-white border border-gray-200 rounded-xl shadow-xl z-50 py-2">
            <button
              onClick={() => {
                onNewSession();
                setDropdownOpen(false);
              }}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-[#FF441F] hover:bg-orange-50 transition-colors"
            >
              <Plus size={14} />
              <span className="font-medium">Nueva sesion</span>
            </button>
            {sessions.length > 0 && (
              <div className="border-t border-gray-100 mt-1 pt-1">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => handleSelectSession(session)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 transition-colors truncate ${
                      session.id === activeSessionId
                        ? 'text-[#FF441F] bg-orange-50/50'
                        : 'text-gray-700'
                    }`}
                  >
                    {session.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right: new session button */}
      <button
        onClick={onNewSession}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-[#FF441F] text-white text-sm font-medium hover:bg-[#E03A18] rounded-lg shadow-sm transition-colors"
      >
        <Plus size={14} />
        <span className="hidden sm:inline">Nueva sesion</span>
      </button>
    </header>
  );
}
