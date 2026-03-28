export type MessageType = 'user' | 'bot';
export type ResponseType = 'text' | 'table' | 'line-chart' | 'bar-chart' | 'error';

export interface TableColumn {
  key: string;
  label: string;
  align?: 'left' | 'right' | 'center';
  type?: 'text' | 'number' | 'badge' | 'delta';
}

export interface TableData {
  title: string;
  columns: TableColumn[];
  rows: Record<string, string | number>[];
}

export interface ChartDataPoint {
  label: string;
  value: number;
  value2?: number;
}

export interface ChartData {
  title: string;
  points: ChartDataPoint[];
  yAxisLabel?: string;
  xAxisLabel?: string;
  series?: { key: string; label: string; color: string }[];
}

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
  responseType?: ResponseType;
  tableData?: TableData;
  chartData?: ChartData;
  processingStage?: string | null;
}

export interface Session {
  id: string;
  name: string;
  timestamp: Date;
  messages: Message[];
  preview?: string;
}

export interface ProactiveSuggestion {
  id: string;
  text: string;
  category: string;
}
