"use client";

import type { ResponseType, TableData, ChartData } from '@/types/api';
import { DataTable } from './data-table';
import { LineChartCard } from './line-chart-card';
import { BarChartCard } from './bar-chart-card';

interface DynamicChartProps {
  responseType: ResponseType;
  tableData?: TableData;
  chartData?: ChartData;
}

export function DynamicChart({ responseType, tableData, chartData }: DynamicChartProps) {
  if (responseType === 'table' && tableData) {
    return <DataTable data={tableData} />;
  }
  if (responseType === 'line-chart' && chartData) {
    return <LineChartCard data={chartData} />;
  }
  if (responseType === 'bar-chart' && chartData) {
    return <BarChartCard data={chartData} />;
  }
  return null;
}
