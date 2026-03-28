"use client";

import { Copy, Download } from 'lucide-react';
import { useCallback } from 'react';

interface ChartContainerProps {
  title: string;
  children: React.ReactNode;
  footerLabel?: string;
  onCopy?: () => void;
  onExport?: () => void;
}

export function ChartContainer({
  title,
  children,
  footerLabel,
  onCopy,
  onExport,
}: ChartContainerProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm mt-3">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
        <h4 className="text-sm font-semibold text-gray-800">{title}</h4>
      </div>

      {/* Chart area */}
      <div className="px-4 py-4">{children}</div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-gray-100 flex items-center justify-between bg-gray-50/50">
        <div className="flex items-center gap-2">
          {onCopy && (
            <button
              onClick={onCopy}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-[#FF441F] transition-colors"
            >
              <Copy size={12} />
              Copiar
            </button>
          )}
          {onExport && (
            <button
              onClick={onExport}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-[#FF441F] transition-colors"
            >
              <Download size={12} />
              Exportar CSV
            </button>
          )}
        </div>
        {footerLabel && (
          <span className="text-xs text-gray-400">{footerLabel}</span>
        )}
      </div>
    </div>
  );
}

export function useChartExport() {
  const copyToClipboard = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback: no-op
    }
  }, []);

  const downloadCSV = useCallback((filename: string, csvContent: string) => {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, []);

  return { copyToClipboard, downloadCSV };
}
