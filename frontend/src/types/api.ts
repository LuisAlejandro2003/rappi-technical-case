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
  [key: string]: string | number;
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
  followUpSuggestions?: string[];
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

// --- Insights System ---

export type InsightSeverity = 'Alta' | 'Media' | 'Baja';
export type InsightCategoryId = 'anomalias' | 'tendencias' | 'benchmarking' | 'correlaciones' | 'oportunidades';

export interface InsightFinding {
  id: string;
  category: InsightCategoryId;
  severity: number;
  title: string;
  description: string;
  zone: string | null;
  city: string | null;
  country: string | null;
  metrics: string[];
  magnitude: number;
  direction: 'improvement' | 'deterioration' | 'neutral';
  recommendation: string;
  explore_query: string;
}

export interface InsightReport {
  id: string;
  generated_at: string;
  executive_summary: string;
  findings: InsightFinding[];
  category_counts: Record<string, number>;
  markdown_report: string;
  narrative_sections: Record<string, string>;
}

export interface InsightProgress {
  step: string;
  label: string;
  status: 'running' | 'done';
  step_number: number;
  total_steps: number;
  findings_count?: number;
}
