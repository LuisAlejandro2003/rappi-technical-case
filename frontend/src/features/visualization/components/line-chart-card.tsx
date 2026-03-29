"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ChartContainer, useChartExport } from './chart-container';
import { ChartTooltip } from './chart-tooltip';
import type { ChartData } from '@/types/api';
import { useCallback } from 'react';

interface LineChartCardProps {
  data: ChartData;
}

export function LineChartCard({ data }: LineChartCardProps) {
  const { title, points, yAxisLabel, xAxisLabel, series } = data;
  const { copyToClipboard, downloadCSV } = useChartExport();

  const handleCopy = useCallback(() => {
    const seriesLabels = series?.map((s) => s.label) || [yAxisLabel || 'Value'];
    const header = `${xAxisLabel || 'Label'}\t${seriesLabels.join('\t')}`;
    const body = points.map((p) => {
      const vals = (series || [{ key: 'value' }]).map((s) => p[s.key] ?? '');
      return `${p.label}\t${vals.join('\t')}`;
    }).join('\n');
    copyToClipboard(`${header}\n${body}`);
  }, [points, xAxisLabel, yAxisLabel, series, copyToClipboard]);

  const handleExport = useCallback(() => {
    const seriesLabels = series?.map((s) => s.label) || [yAxisLabel || 'Value'];
    const header = `"${xAxisLabel || 'Label'}",${seriesLabels.map((l) => `"${l}"`).join(',')}`;
    const body = points.map((p) => {
      const vals = (series || [{ key: 'value' }]).map((s) => p[s.key] ?? '');
      return `"${p.label}",${vals.join(',')}`;
    }).join('\n');
    downloadCSV(title.replace(/\s+/g, '_'), `${header}\n${body}`);
  }, [title, points, xAxisLabel, yAxisLabel, series, downloadCSV]);

  return (
    <ChartContainer
      title={title}
      footerLabel={`${points.length} periodos`}
      onCopy={handleCopy}
      onExport={handleExport}
    >
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={points} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: '#9CA3AF' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
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
          {series && series.length > 0 ? (
            series.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={2.5}
                dot={{ fill: s.color, stroke: 'white', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))
          ) : (
            <Line
              type="monotone"
              dataKey="value"
              name={yAxisLabel || 'Valor'}
              stroke="#FF441F"
              strokeWidth={2.5}
              dot={{ fill: '#FF441F', stroke: 'white', strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
