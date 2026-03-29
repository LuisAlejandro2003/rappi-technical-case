"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { ChartContainer, useChartExport } from './chart-container';
import { ChartTooltip } from './chart-tooltip';
import type { ChartData } from '@/types/api';
import { useCallback } from 'react';

const BAR_COLORS = [
  '#FF441F',
  '#FF6B45',
  '#FF8C6B',
  '#FFAD91',
  '#FFCDB7',
  '#FFA07A',
  '#FF7A5C',
];

interface BarChartCardProps {
  data: ChartData;
}

export function BarChartCard({ data }: BarChartCardProps) {
  const { title, points, yAxisLabel, xAxisLabel } = data;
  const { copyToClipboard, downloadCSV } = useChartExport();

  const values = points.map((p) => Number(p.value) || 0);
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);
  const yDomain: [number, number] = [
    minValue < 0 ? Math.floor(minValue * 1.15) : 0,
    Math.ceil(maxValue * 1.15),
  ];

  const handleCopy = useCallback(() => {
    const header = `${xAxisLabel || 'Label'}\t${yAxisLabel || 'Value'}`;
    const body = points.map((p) => `${p.label}\t${p.value}`).join('\n');
    copyToClipboard(`${header}\n${body}`);
  }, [points, xAxisLabel, yAxisLabel, copyToClipboard]);

  const handleExport = useCallback(() => {
    const header = `"${xAxisLabel || 'Label'}","${yAxisLabel || 'Value'}"`;
    const body = points.map((p) => `"${p.label}",${p.value}`).join('\n');
    downloadCSV(title.replace(/\s+/g, '_'), `${header}\n${body}`);
  }, [title, points, xAxisLabel, yAxisLabel, downloadCSV]);

  return (
    <ChartContainer
      title={title}
      footerLabel={`${points.length} categorias`}
      onCopy={handleCopy}
      onExport={handleExport}
    >
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={points} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: '#9CA3AF' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={yDomain}
            tick={{ fontSize: 11, fill: '#9CA3AF' }}
            axisLine={false}
            tickLine={false}
            label={
              yAxisLabel
                ? {
                    value: yAxisLabel,
                    angle: -90,
                    position: 'insideLeft',
                    style: { fontSize: 11, fill: '#9CA3AF' },
                  }
                : undefined
            }
          />
          <Tooltip content={<ChartTooltip />} />
          {minValue < 0 && <ReferenceLine y={0} stroke="#9CA3AF" strokeDasharray="3 3" />}
          <Bar
            dataKey="value"
            name={yAxisLabel || 'Valor'}
            radius={[4, 4, 0, 0]}
            maxBarSize={48}
          >
            {points.map((point, index) => (
              <Cell
                key={`cell-${index}`}
                fill={(Number(point.value) || 0) < 0 ? '#EF4444' : BAR_COLORS[index % BAR_COLORS.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
