import { useState, useEffect } from 'react';
import {
  Clock,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  Calendar,
  Timer,
  Layers,
  History,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { StatusBadge } from '../components/ui/StatusBadge';
import { api } from '../services/api';

export default function HistoryPage() {
  const [groupedExecutions, setGroupedExecutions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedExecId, setExpandedExecId] = useState<number | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const data = await api.getHistory();

        // Group by execution_id
        const groups: { [key: number]: any } = {};
        for (const item of (data || [])) {
          const eId = item.execution_id || 1;
          if (!groups[eId]) {
            groups[eId] = {
              execution_id: eId,
              timestamp: item.timestamp,
              tests: [],
              passed: 0,
              failed: 0,
              duration_ms: 0,
            };
          }
          groups[eId].tests.push(item);
          if (item.status === 'passed') {
            groups[eId].passed += 1;
          } else {
            groups[eId].failed += 1;
          }
          groups[eId].duration_ms += (item.duration_ms || 0);
        }

        const sorted = Object.values(groups).sort((a: any, b: any) => b.execution_id - a.execution_id);
        setGroupedExecutions(sorted);
        if (sorted.length > 0) {
          setExpandedExecId(sorted[0].execution_id);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to fetch test execution history');
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const totalRuns = groupedExecutions.reduce((sum, g) => sum + g.tests.length, 0);
  const totalPassed = groupedExecutions.reduce((sum, g) => sum + g.passed, 0);
  const overallPassPct = totalRuns > 0 ? Math.round((totalPassed / totalRuns) * 100) : 0;

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/15 text-purple-300 text-[11px] font-semibold uppercase tracking-wider mb-2 backdrop-blur-md">
          <History className="w-3.5 h-3.5 text-purple-400" />
          <span>Execution Telemetry</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Regression Execution Timeline
        </h1>
        <p className="text-sm text-slate-400 mt-1 max-w-2xl">
          Historical log of every Playwright test session and regression failure trajectory recorded in Supabase.
        </p>
      </div>

      {/* Summary KPI Cards (Floating Midnight Glass) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-5 text-center rounded-2xl">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">Total Recorded Sessions</span>
          <span className="text-3xl font-extrabold text-white">{groupedExecutions.length}</span>
        </Card>
        <Card className="p-5 text-center rounded-2xl">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">Total Test Executions</span>
          <span className="text-3xl font-extrabold text-purple-300">{totalRuns}</span>
        </Card>
        <Card className="p-5 text-center rounded-2xl">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">Historical Pass Rate</span>
          <span className="text-3xl font-extrabold text-emerald-400">{overallPassPct}%</span>
        </Card>
      </div>

      {loading ? (
        <LoadingState message="Querying execution history from Supabase..." />
      ) : error ? (
        <div className="p-5 rounded-2xl bg-rose-950/30 border border-rose-500/30 text-rose-200 text-sm">
          {error}
        </div>
      ) : groupedExecutions.length === 0 ? (
        <Card className="p-12 text-center rounded-[28px]">
          <EmptyState
            icon={Clock}
            title="No execution history recorded yet"
            description="Run test executions via the Execution page to populate your regression timeline."
          />
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
            Recorded Execution Sessions ({groupedExecutions.length})
          </div>

          <div className="space-y-4">
            {groupedExecutions.map((exec, idx) => {
              const total = exec.tests.length;
              const passPct = total > 0 ? Math.round((exec.passed / total) * 100) : 0;
              const isExpanded = expandedExecId === exec.execution_id;

              return (
                <Card
                  key={exec.execution_id}
                  className="overflow-hidden transition-all rounded-2xl"
                >
                  <div
                    onClick={() => setExpandedExecId(isExpanded ? null : exec.execution_id)}
                    className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer select-none hover:bg-white/5 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-2xl bg-purple-500/15 border border-purple-500/25 flex items-center justify-center text-purple-300 font-mono font-bold text-sm shrink-0">
                        #{exec.execution_id}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-extrabold text-base text-white">
                            Execution Session #{exec.execution_id}
                          </h3>
                          <StatusBadge status={exec.failed === 0 ? 'passed' : 'failed'} size="sm" />
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/10 text-slate-300 font-bold">
                            Run {groupedExecutions.length - idx}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-slate-400 mt-1.5 flex-wrap font-mono">
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5 text-purple-400" />
                            {exec.timestamp ? new Date(exec.timestamp).toLocaleString() : 'Recent'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Timer className="w-3.5 h-3.5 text-purple-400" />
                            {(exec.duration_ms / 1000).toFixed(2)}s runtime
                          </span>
                          <span className="flex items-center gap-1 text-slate-300">
                            <Layers className="w-3.5 h-3.5 text-purple-400" />
                            {total} tests
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-5 sm:self-center">
                      <div className="text-right">
                        <span className={`font-mono font-extrabold text-base ${exec.failed === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {passPct}% Pass Rate
                        </span>
                        <span className="block text-[11px] font-mono text-slate-400">
                          {exec.passed} passed • {exec.failed} failed
                        </span>
                      </div>

                      <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-slate-400">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Test Items */}
                  {isExpanded && (
                    <div className="border-t border-white/10 bg-[#0B0F19]/60 p-5 space-y-3">
                      <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                        Session Test Breakdown ({exec.tests.length} tests)
                      </div>
                      <div className="space-y-2">
                        {exec.tests.map((t: any, tIdx: number) => {
                          const isPass = t.status === 'passed';
                          return (
                            <div
                              key={t.id || tIdx}
                              className="p-3.5 rounded-2xl bg-[#0F172A] border border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-xs"
                            >
                              <div className="flex items-start gap-3 min-w-0">
                                <div className="mt-0.5 shrink-0">
                                  {isPass ? (
                                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                  ) : (
                                    <XCircle className="w-4 h-4 text-rose-400" />
                                  )}
                                </div>
                                <div className="min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="font-mono text-xs font-bold text-purple-300">
                                      {t.test_id || `TC-${tIdx + 1}`}
                                    </span>
                                    {t.failure_category && (
                                      <span className="font-mono text-[9px] font-semibold text-rose-300 px-2 py-0.5 rounded-full bg-rose-950/60 border border-rose-800/50">
                                        {t.failure_category}
                                      </span>
                                    )}
                                    <span className="text-xs font-bold text-white truncate max-w-xs sm:max-w-md">
                                      {t.test_name || 'Automated Step Execution'}
                                    </span>
                                  </div>
                                  {t.error_message && (
                                    <p className="text-[11px] text-rose-300 font-mono mt-1 bg-rose-950/30 p-2 rounded-lg border border-rose-500/20">
                                      {t.error_message}
                                    </p>
                                  )}
                                </div>
                              </div>

                              <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                                <span className="text-xs font-mono text-slate-400">
                                  {((t.duration_ms || 0) / 1000).toFixed(2)}s
                                </span>
                                <StatusBadge status={t.status} size="sm" />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
