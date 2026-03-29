"use client";

import { BarChart2, Map, Award, TrendingUp, AlertTriangle } from 'lucide-react';
import { motion } from 'motion/react';
import { SuggestionChip } from './suggestion-chip';

interface WelcomeCardProps {
  onSuggestionClick: (text: string) => void;
}

const suggestions = [
  { icon: Map, text: 'Top 10 zonas con mayor volumen de ordenes esta semana' },
  { icon: Award, text: 'Compara Perfect Orders entre zonas Wealthy y Non Wealthy en Mexico' },
  { icon: TrendingUp, text: 'Evolucion de Gross Profit UE por pais en las ultimas 8 semanas' },
  { icon: AlertTriangle, text: 'Cuales son las zonas problematicas con metricas deterioradas?' },
];

export function WelcomeCard({ onSuggestionClick }: WelcomeCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center text-center py-16 px-4"
    >
      {/* Bot avatar */}
      <div className="w-14 h-14 rounded-2xl bg-[#FF441F] shadow-lg flex items-center justify-center mb-5">
        <BarChart2 size={24} color="white" />
      </div>

      <h2 className="text-xl font-semibold text-gray-900 mb-2">
        Rappi Analytics Assistant
      </h2>
      <p className="text-sm text-gray-500 max-w-md mb-8 leading-relaxed">
        Pregunta sobre metricas operacionales por zona, ordenes, rentabilidad,
        adopcion y calidad de servicio. Puedo generar tablas y graficos con datos en tiempo real.
      </p>

      {/* Suggestion chips */}
      <div className="flex flex-wrap justify-center gap-3 max-w-lg">
        {suggestions.map((s) => (
          <SuggestionChip
            key={s.text}
            icon={s.icon}
            text={s.text}
            onClick={onSuggestionClick}
          />
        ))}
      </div>
    </motion.div>
  );
}
