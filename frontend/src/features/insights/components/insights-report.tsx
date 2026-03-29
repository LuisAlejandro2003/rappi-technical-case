"use client";

import { useState, useEffect, useRef } from 'react';
import {
  AlertTriangle,
  TrendingUp,
  BarChart2,
  Share2,
  Lightbulb,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  MessageSquare,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Download,
  type LucideIcon,
} from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import type { InsightReport as InsightReportType, InsightFinding, InsightCategoryId } from '@/types/api';
import { MarkdownRenderer } from '@/features/chat/components/markdown-renderer';
import { useInsightsStore } from '@/stores/insights-store';

/* ---------- helpers ---------- */

const CATEGORY_CONFIG: Record<string, { icon: LucideIcon; color: string; bgColor: string; label: string }> = {
  anomalias:      { icon: AlertTriangle, color: '#EF4444', bgColor: '#FEF2F2', label: 'Anomalias' },
  tendencias:     { icon: TrendingUp,    color: '#FF441F', bgColor: '#FFF5F3', label: 'Tendencias' },
  benchmarking:   { icon: BarChart2,     color: '#3B82F6', bgColor: '#EFF6FF', label: 'Benchmarking' },
  correlaciones:  { icon: Share2,        color: '#8B5CF6', bgColor: '#F5F3FF', label: 'Correlaciones' },
  oportunidades:  { icon: Lightbulb,     color: '#10B981', bgColor: '#ECFDF5', label: 'Oportunidades' },
};

function directionIcon(d: InsightFinding['direction']) {
  if (d === 'improvement') return <ArrowUpRight size={14} className="text-green-500" />;
  if (d === 'deterioration') return <ArrowDownRight size={14} className="text-red-500" />;
  return <Minus size={14} className="text-gray-400" />;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('es-CO', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

/* ---------- sub-components ---------- */

function SummaryCards({ categoryCounts }: { categoryCounts: Record<string, number> }) {
  const total = Object.values(categoryCounts).reduce((a, b) => a + b, 0);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <p className="text-xs text-gray-500 mb-1">Total hallazgos</p>
        <p className="text-2xl font-bold text-gray-800">{total}</p>
      </div>
      {Object.entries(CATEGORY_CONFIG).map(([key, cfg]) => {
        const count = categoryCounts[key] ?? 0;
        const Icon = cfg.icon;
        return (
          <div key={key} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-1.5 mb-1">
              <Icon size={13} style={{ color: cfg.color }} />
              <p className="text-xs text-gray-500">{cfg.label}</p>
            </div>
            <p className="text-2xl font-bold" style={{ color: cfg.color }}>{count}</p>
          </div>
        );
      })}
    </div>
  );
}

function InsightCard({
  finding,
  onExplore,
}: {
  finding: InsightFinding;
  onExplore: (query: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const catCfg = CATEGORY_CONFIG[finding.category];

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 border-l-4 overflow-hidden"
      style={{ borderLeftColor: catCfg?.color || '#9CA3AF' }}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {finding.zone && (
              <span className="text-[10px] text-gray-500 font-medium">{finding.zone}{finding.country ? `, ${finding.country}` : ''}</span>
            )}
            {finding.country && !finding.zone && (
              <span className="text-[10px] text-gray-500 font-medium">{finding.country}</span>
            )}
            <span className="ml-auto flex items-center gap-1">
              {directionIcon(finding.direction)}
            </span>
          </div>
          <h4 className="text-sm font-semibold text-gray-800">{finding.title}</h4>
        </div>
        <div className="flex-shrink-0 mt-1 text-gray-400">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-3 border-t border-gray-100 pt-3">
              <p className="text-sm text-gray-600 leading-relaxed">{finding.description}</p>

              {finding.metrics.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {finding.metrics.map((m) => (
                    <span key={m} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-[10px]">
                      {m}
                    </span>
                  ))}
                </div>
              )}

              {finding.recommendation && (
                <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
                  <p className="text-xs font-semibold text-blue-700 mb-1">Recomendacion</p>
                  <p className="text-xs text-blue-600 leading-relaxed">{finding.recommendation}</p>
                </div>
              )}

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onExplore(finding.explore_query);
                }}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-[#FF441F] hover:underline"
              >
                <MessageSquare size={12} />
                Explorar en chat
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function CategorySection({
  categoryId,
  findings,
  narrative,
  onExplore,
}: {
  categoryId: string;
  findings: InsightFinding[];
  narrative?: string;
  onExplore: (query: string) => void;
}) {
  const cfg = CATEGORY_CONFIG[categoryId];
  if (!cfg || (findings.length === 0 && !narrative)) return null;

  const Icon = cfg.icon;
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div id={`section-${categoryId}`} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-2.5 p-4 hover:bg-gray-50/50 transition-colors"
      >
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: cfg.bgColor }}
        >
          <Icon size={14} style={{ color: cfg.color }} />
        </div>
        <h3 className="text-sm font-bold text-gray-800 flex-1 text-left">{cfg.label}</h3>
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{findings.length} hallazgos</span>
        <div className="text-gray-400">
          {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-3">
              {/* LLM narrative for this category */}
              {narrative && (
                <div className="text-sm text-gray-600 leading-relaxed border-b border-gray-100 pb-3">
                  <MarkdownRenderer content={narrative} />
                </div>
              )}

              {/* Finding cards */}
              {findings
                .sort((a, b) => b.severity - a.severity)
                .map((f) => (
                  <InsightCard key={f.id} finding={f} onExplore={onExplore} />
                ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ---------- main component ---------- */

interface InsightsReportProps {
  report: InsightReportType;
  onRegenerate: () => void;
  onExploreInChat: (query: string) => void;
}

function exportMarkdown(report: InsightReportType) {
  const content = report.markdown_report || report.executive_summary || 'No report content';
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `rappi-insights-${new Date().toISOString().slice(0, 10)}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export function InsightsReport({ report, onRegenerate, onExploreInChat }: InsightsReportProps) {
  const activeSection = useInsightsStore((s) => s.activeSection);
  const prevSectionRef = useRef(activeSection);

  // Scroll to section when activeSection changes
  useEffect(() => {
    if (activeSection !== prevSectionRef.current) {
      prevSectionRef.current = activeSection;
      const el = document.getElementById(`section-${activeSection}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [activeSection]);

  // Group findings by category
  const grouped = report.findings.reduce<Record<string, InsightFinding[]>>((acc, f) => {
    if (!acc[f.category]) acc[f.category] = [];
    acc[f.category].push(f);
    return acc;
  }, {});

  // Top findings for executive summary
  const topFindings = [...report.findings]
    .sort((a, b) => b.severity - a.severity)
    .slice(0, 5);

  const narrativeSections = report.narrative_sections || {};

  return (
    <div className="flex-1 overflow-y-auto bg-[#F8F9FA]">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-800">Reporte de Insights</h1>
            <p className="text-xs text-gray-400 mt-1">
              Generado: {formatDate(report.generated_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => exportMarkdown(report)}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Download size={13} />
              Exportar MD
            </button>
            <button
              onClick={onRegenerate}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-white bg-[#FF441F] rounded-lg hover:shadow-md transition-all"
            >
              <RefreshCw size={13} />
              Regenerar
            </button>
          </div>
        </div>

        {/* Summary cards */}
        <SummaryCards categoryCounts={report.category_counts} />

        {/* Executive summary */}
        <div id="section-resumen" className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-bold text-gray-800 mb-3">Resumen Ejecutivo</h2>

          {narrativeSections.resumen ? (
            <div className="text-sm text-gray-600 leading-relaxed mb-4">
              <MarkdownRenderer content={narrativeSections.resumen} />
            </div>
          ) : report.executive_summary ? (
            <div className="text-sm text-gray-600 leading-relaxed mb-4">
              <MarkdownRenderer content={report.executive_summary} />
            </div>
          ) : null}

          {topFindings.length > 0 && (
            <div className="border-t border-gray-100 pt-3">
              <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">
                Hallazgos principales
              </p>
              <div className="space-y-2">
                {topFindings.map((f) => {
                  const cfg = CATEGORY_CONFIG[f.category];
                  const Icon = cfg?.icon || AlertTriangle;
                  return (
                    <div key={f.id} className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                      <Icon size={13} style={{ color: cfg?.color || '#666' }} />
                      <span className="text-sm text-gray-700 flex-1 truncate">{f.title}</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ backgroundColor: cfg?.bgColor, color: cfg?.color }}>
                        {cfg?.label || f.category}
                      </span>
                      {directionIcon(f.direction)}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Category sections — each with its narrative + cards */}
        {(['anomalias', 'tendencias', 'benchmarking', 'correlaciones', 'oportunidades'] as InsightCategoryId[]).map(
          (catId) => (
            <CategorySection
              key={catId}
              categoryId={catId}
              findings={grouped[catId] || []}
              narrative={narrativeSections[catId]}
              onExplore={onExploreInChat}
            />
          )
        )}
      </div>
    </div>
  );
}
