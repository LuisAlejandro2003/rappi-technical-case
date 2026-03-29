"use client";

import { Zap } from 'lucide-react';
import { motion } from 'motion/react';

const STEPS = [
  'Detectando anomalias...',
  'Analizando tendencias...',
  'Comparando zonas...',
  'Buscando correlaciones...',
  'Identificando oportunidades...',
  'Generando reporte narrativo...',
];

export function InsightsLoading() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-[#F8F9FA] p-6 gap-8">
      <div className="w-16 h-16 rounded-2xl bg-[#FF441F] flex items-center justify-center shadow-lg">
        <Zap size={28} color="white" />
      </div>

      <div className="text-center">
        <h2 className="text-lg font-bold text-gray-800 mb-1">Analizando datos</h2>
        <p className="text-sm text-gray-500">Esto puede tomar unos segundos...</p>
      </div>

      <div className="w-full max-w-xs space-y-3">
        {STEPS.map((label, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="flex items-center gap-3"
          >
            <div className="w-2 h-2 rounded-full bg-[#FF441F] flex-shrink-0" />
            <span className="text-sm text-gray-600">{label}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
