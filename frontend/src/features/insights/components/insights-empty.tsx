"use client";

import { BarChart2, Zap } from 'lucide-react';
import { motion } from 'motion/react';

interface InsightsEmptyProps {
  onGenerate: () => void;
}

export function InsightsEmpty({ onGenerate }: InsightsEmptyProps) {
  return (
    <div className="flex-1 flex items-center justify-center bg-[#F8F9FA] p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center max-w-md"
      >
        <div className="mx-auto w-16 h-16 rounded-2xl bg-orange-50 flex items-center justify-center mb-6">
          <BarChart2 size={32} className="text-[#FF441F]" />
        </div>

        <h2 className="text-xl font-bold text-gray-800 mb-2">
          Insights Automaticos
        </h2>
        <p className="text-sm text-gray-500 leading-relaxed mb-8">
          Genera un reporte inteligente que analiza tus datos operacionales,
          detecta anomalias, identifica tendencias y encuentra oportunidades
          de mejora.
        </p>

        <button
          onClick={onGenerate}
          className="inline-flex items-center gap-2 px-6 py-3 bg-[#FF441F] text-white text-sm font-semibold rounded-xl hover:shadow-lg hover:shadow-[#FF441F]/20 active:scale-[0.98] transition-all"
        >
          <Zap size={16} />
          Generar Reporte
        </button>

        <p className="text-xs text-gray-400 mt-4">
          El analisis toma aproximadamente 1-2 minutos
        </p>
      </motion.div>
    </div>
  );
}
