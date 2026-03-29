"use client";

import { useMemo } from 'react';
import type { ChartData, ChartDataPoint } from '@/types/api';

export function useChartData(data: ChartData | undefined) {
  const formattedPoints = useMemo(() => {
    if (!data?.points) return [];
    return data.points.map((p: ChartDataPoint) => ({
      ...p,
      label: p.label,
      value: Number(p.value),
      ...(p.value2 !== undefined ? { value2: Number(p.value2) } : {}),
    }));
  }, [data?.points]);

  return {
    points: formattedPoints,
    title: data?.title || '',
    yAxisLabel: data?.yAxisLabel,
    xAxisLabel: data?.xAxisLabel,
    series: data?.series,
  };
}
