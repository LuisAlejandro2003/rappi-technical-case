"use client";

import { useEffect } from 'react';
import { useInsightsStore } from '@/stores/insights-store';
import { InsightsEmpty } from './insights-empty';
import { InsightsLoading } from './insights-loading';
import { InsightsReport } from './insights-report';

interface InsightsViewProps {
  onExploreInChat: (query: string) => void;
}

export function InsightsView({ onExploreInChat }: InsightsViewProps) {
  const { report, isGenerating, fetchCachedReport, generateReport } = useInsightsStore();

  useEffect(() => {
    fetchCachedReport();
  }, [fetchCachedReport]);

  if (isGenerating) {
    return <InsightsLoading />;
  }

  if (!report) {
    return <InsightsEmpty onGenerate={generateReport} />;
  }

  return (
    <InsightsReport
      report={report}
      onRegenerate={generateReport}
      onExploreInChat={onExploreInChat}
    />
  );
}
