import type { ChartData, ChartDataPoint, TableData, ResponseType } from '@/types/api';

/** Palette with enough distinct colors for multi-series charts */
export const CHART_COLORS = [
  '#FF441F', '#2563EB', '#16A34A', '#D97706', '#7C3AED',
  '#DB2777', '#0891B2', '#65A30D', '#EA580C', '#4F46E5',
];

/** Backend VizConfig shape (matches backend VizConfig pydantic model) */
export interface VizConfig {
  type: 'line' | 'bar' | 'table';
  title: string;
  x_axis?: string[];
  series?: Array<{ name: string; data: (number | null)[] }>;
  raw_data?: Record<string, string | number>[] | null;
}

/** Convert backend VizConfig to frontend ChartData format */
export function vizConfigToChartData(data: VizConfig | Record<string, unknown>): ChartData {
  const xAxis = (data.x_axis as string[]) || [];
  const series = (data.series as Array<{ name: string; data: number[] }>) || [];

  // Build chart points with a dynamic key per series
  const points: ChartDataPoint[] = xAxis.map((label, i) => {
    const point: ChartDataPoint = { label };
    series.forEach((s, si) => {
      const key = si === 0 ? 'value' : `value${si + 1}`;
      point[key] = s.data[i] ?? 0;
    });
    return point;
  });

  return {
    title: (data.title as string) || '',
    points,
    series: series.map((s, i) => ({
      key: i === 0 ? 'value' : `value${i + 1}`,
      label: s.name,
      color: CHART_COLORS[i % CHART_COLORS.length],
    })),
  };
}

/** Convert backend VizConfig to frontend TableData format */
export function vizConfigToTableData(data: VizConfig | Record<string, unknown>): TableData {
  return {
    title: (data.title as string) || '',
    columns: ((data.x_axis as string[]) || []).map((col) => ({
      key: col,
      label: col,
    })),
    rows: (data.raw_data as Record<string, string | number>[]) || [],
  };
}

/** Determine frontend ResponseType from backend viz type */
export function vizTypeToResponseType(vizType: string): ResponseType {
  switch (vizType) {
    case 'line': return 'line-chart';
    case 'bar': return 'bar-chart';
    case 'table': return 'table';
    default: return 'text';
  }
}
