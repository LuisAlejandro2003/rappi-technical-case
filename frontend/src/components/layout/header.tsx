"use client";

import { BarChart2, Plus, Menu, Database } from 'lucide-react';
import { useSessionStore } from '@/stores/session-store';

interface DataFreshness {
  last_updated: string;
  tables: Record<string, number>;
}

interface HeaderProps {
  onToggleSidebar: () => void;
  onNewSession: () => void;
  dataFreshness?: DataFreshness | null;
}

export function Header({ onToggleSidebar, onNewSession, dataFreshness }: HeaderProps) {
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

      {/* Right: data freshness + new session */}
      <div className="flex items-center gap-2">
        {dataFreshness && (
          <div className="hidden md:flex items-center gap-1.5 text-xs text-gray-400">
            <Database size={12} />
            <span>{dataFreshness.last_updated}</span>
          </div>
        )}

        <button
          onClick={onNewSession}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#FF441F] text-white text-sm font-medium hover:bg-[#E03A18] rounded-lg shadow-sm transition-colors"
        >
          <Plus size={14} />
          <span className="hidden sm:inline">Nueva sesion</span>
        </button>
      </div>
    </header>
  );
}
