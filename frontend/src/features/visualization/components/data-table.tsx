"use client";

import { Copy, Download } from 'lucide-react';
import { useCallback } from 'react';
import type { TableData } from '@/types/api';

interface DataTableProps {
  data: TableData;
}

function DeltaBadge({ value }: { value: string | number }) {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  const isPositive = num >= 0;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
        isPositive ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
      }`}
    >
      {isPositive ? '+' : ''}
      {typeof value === 'number' ? value.toFixed(1) : value}%
    </span>
  );
}

function StatusBadge({ value }: { value: string | number }) {
  const text = String(value);
  let colorClass = 'bg-gray-100 text-gray-700';
  if (text === 'Critico' || text === 'Critica') colorClass = 'bg-red-100 text-red-700';
  else if (text === 'Alerta') colorClass = 'bg-amber-100 text-amber-700';
  else if (text === 'Normal' || text === 'Bueno') colorClass = 'bg-green-100 text-green-700';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {text}
    </span>
  );
}

export function DataTable({ data }: DataTableProps) {
  const { title, columns, rows } = data;

  const handleCopy = useCallback(async () => {
    const header = columns.map((c) => c.label).join('\t');
    const body = rows
      .map((row) => columns.map((c) => row[c.key] ?? '').join('\t'))
      .join('\n');
    try {
      await navigator.clipboard.writeText(`${header}\n${body}`);
    } catch {
      // no-op
    }
  }, [columns, rows]);

  const handleExport = useCallback(() => {
    const header = columns.map((c) => `"${c.label}"`).join(',');
    const body = rows
      .map((row) =>
        columns.map((c) => {
          const val = row[c.key] ?? '';
          return typeof val === 'string' ? `"${val}"` : val;
        }).join(',')
      )
      .join('\n');
    const csv = `${header}\n${body}`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${title.replace(/\s+/g, '_')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [title, columns, rows]);

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm mt-3">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
        <h4 className="text-sm font-semibold text-gray-800">{title}</h4>
      </div>

      {/* Table */}
      <div className="overflow-auto" style={{ maxHeight: 320 }}>
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white">
            <tr className="border-b border-gray-100">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap ${
                    col.align === 'right'
                      ? 'text-right'
                      : col.align === 'center'
                      ? 'text-center'
                      : 'text-left'
                  }`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className="border-b border-gray-50 hover:bg-orange-50/30 transition-colors"
              >
                {columns.map((col) => {
                  const value = row[col.key];
                  return (
                    <td
                      key={col.key}
                      className={`px-4 py-2.5 whitespace-nowrap ${
                        col.align === 'right'
                          ? 'text-right'
                          : col.align === 'center'
                          ? 'text-center'
                          : 'text-left'
                      }`}
                    >
                      {col.type === 'delta' ? (
                        <DeltaBadge value={value} />
                      ) : col.type === 'badge' ? (
                        <StatusBadge value={value} />
                      ) : col.type === 'number' ? (
                        <span className="font-medium text-gray-800">
                          {typeof value === 'number' ? value.toLocaleString() : value}
                        </span>
                      ) : (
                        <span className="text-gray-700">{String(value)}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-gray-100 flex items-center justify-between bg-gray-50/50">
        <div className="flex items-center gap-3">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-[#FF441F] transition-colors"
          >
            <Copy size={12} />
            Copiar
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-[#FF441F] transition-colors"
          >
            <Download size={12} />
            Exportar CSV
          </button>
        </div>
        <span className="text-xs text-gray-400">{rows.length} filas</span>
      </div>
    </div>
  );
}
