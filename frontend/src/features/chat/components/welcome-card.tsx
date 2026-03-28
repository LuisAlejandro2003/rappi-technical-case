"use client";

import { BarChart2, Map, Award, TrendingUp, AlertTriangle } from 'lucide-react';
import { motion } from 'motion/react';
import { SuggestionChip } from './suggestion-chip';

interface WelcomeCardProps {
  onSuggestionClick: (text: string) => void;
}

const suggestions = [
  { icon: Map, text: 'Cobertura por zona en Bogota' },
  { icon: Award, text: 'Top 10 restaurantes por pedidos' },
  { icon: TrendingUp, text: 'Tendencia de ordenes esta semana' },
  { icon: AlertTriangle, text: 'Alertas de tiempos de entrega' },
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
        Pregunta sobre metricas operacionales, rendimiento de restaurantes,
        tiempos de entrega y mas. Puedo generar tablas y graficos con datos en tiempo real.
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
