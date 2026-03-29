"use client";

import { motion } from 'motion/react';
import type { LucideIcon } from 'lucide-react';

interface SuggestionChipProps {
  icon: LucideIcon;
  text: string;
  onClick: (text: string) => void;
}

export function SuggestionChip({ icon: Icon, text, onClick }: SuggestionChipProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick(text)}
      className="px-4 py-2.5 rounded-xl border border-gray-200 bg-white text-sm text-gray-700 hover:border-[#FF441F] hover:text-[#FF441F] hover:bg-orange-50 shadow-sm transition-colors flex items-center gap-2"
    >
      <Icon size={14} />
      <span>{text}</span>
    </motion.button>
  );
}
