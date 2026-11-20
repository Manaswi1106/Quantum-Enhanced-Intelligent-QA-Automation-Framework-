import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Radio,
  Image as ImageIcon,
  X,
  AlertCircle,
  Atom,
  Layers,
  Globe,
  Terminal,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusBadge } from '../components/ui/StatusBadge';
import { api } from '../services/api';
import type { TestResult } from '../types';

export default function ExecutionPage() {
  const [searchParams] = useSearchParams();
  const paramAppId = searchParams.get('app_id');
  const paramMode = searchParams.get('mode');

  const [applications, setApplications] = useState<any[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [execution, setExecution] = useState<any | null>(null);
  const [results, setResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedScreenshot, setSelectedScreenshot] = useState<string | null>(null);
  const [onlyQaoaSelected, setOnlyQaoaSelected] = useState(paramMode === 'qaoa');
  const [candidateCount, setCandidateCount] = useState<number>(0);
  const [qaoaSelectedCount, setQaoaSelectedCount] = useState<number>(0);

  // Load applications
  useEffect(() => {
    const loadApps = async () => {
      try {
        const apps = await api.getApplications();
        if (apps && apps.length > 0) {
          setApplications(apps);
          const initialId = paramAppId ? parseInt(paramAppId) : apps[0].id;
          setSelectedAppId(initialId);
        }
      } catch (err) {
        console.error('Failed to load apps:', err);
      }
    };
    loadApps();
  }, [paramAppId]);

  // Load test case counts when selectedAppId changes
  useEffect(() => {
    if (!selectedAppId) return;
    const fetchCounts = async () => {
      try {
        const tests = await api.getTestCases(selectedAppId);
        setCandidateCount(tests.length);
        const sel = tests.filter((t: any) => t.status === 'selected');
        setQaoaSelectedCount(sel.length);
        if (paramMode === 'qaoa' && sel.length > 0) {
          setOnlyQaoaSelected(true);
        }
      } catch (err) {
        console.error('Failed to fetch test counts:', err);
      }
    };
    fetchCounts();
  }, [selectedAppId, paramMode]);

  const selectedApp = applications.find((a) => a.id === selectedAppId);

  const handleRunTests = async () => {
    if (!selectedAppId) return;

    try {
      setIsRunning(true);
      setError(null);
      setExecution(null);
      setResults([]);

      let testCaseIds: number[] | undefined = undefined;

      // If user toggled to run QAOA selected only, filter tests
      if (onlyQaoaSelected) {
        const tests = await api.getTestCases(selectedAppId);
        const selectedIds = tests.filter((t: any) => t.status === 'selected').map((t: any) => t.id);
        if (selectedIds.length > 0) {
          testCaseIds = selectedIds;
        } else {
          setError('No QAOA-optimized tests found for this application. Please run QAOA Optimization first or switch to Full Suite mode.');
          setIsRunning(false);
          return;
        }
      }

      const execData = await api.executeTests({
        app_id: selectedAppId,
        test_case_ids: testCaseIds,
      });

      const executionId = execData.id;
      setExecution(execData);

      // Poll real-time status every second
      const pollInterval = setInterval(async () => {
        try {
          const pollData = await api.getExecution(executionId);
          setExecution(pollData);

          if (pollData.results && pollData.results.length > 0) {
            setResults(pollData.results);
          }

          if (pollData.status === 'completed' || pollData.status === 'error') {
            clearInterval(pollInterval);
            setIsRunning(false);
            setResults(pollData.results || []);
          }
        } catch {
          clearInterval(pollInterval);
          setIsRunning(false);
          setError('Lost telemetry connection to running test session.');
        }
      }, 1000);

    } catch (err: any) {
      setError(err.message || 'Failed to start Playwright execution.');
      setIsRunning(false);
    }
  };

  const progressPercent = execution?.progress_percent ?? (
    execution?.total
      ? Math.round(((execution.passed + execution.failed + execution.skipped) / execution.total) * 100)
      : 0
  );

  const passedCount = results.filter((r) => r.status === 'passed').length;
  const failedCount = results.filter((r) => r.status === 'failed' || r.status === 'error').length;
  const totalDuration = results.reduce((acc, curr) => acc + (curr.duration_ms || 0), 0) / 1000;

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/15 text-purple-300 text-[11px] font-semibold uppercase tracking-wider mb-2 backdrop-blur-md">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            <span>Headless Chromium Automation</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Playwright Test Execution
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Real browser automation with live DOM telemetry, assertions, and screenshot captures.
          </p>
        </div>

        {/* Application Selector */}
        {applications.length > 0 && (
          <div className="flex items-center gap-3">
            <div className="bg-[#0F172A] border border-white/15 px-3 py-1.5 rounded-full flex items-center gap-2 shadow-sm">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Target:</span>
              <select
                value={selectedAppId || ''}
                onChange={(e) => setSelectedAppId(Number(e.target.value))}
                disabled={isRunning}
                className="bg-transparent text-white text-xs font-semibold focus:outline-none cursor-pointer py-1"
              >
                {applications.map((app) => (
                  <option key={app.id} value={app.id} className="bg-[#0F172A] text-white">
                    {app.name || app.url} (ID: {app.id})
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/30 border border-rose-500/30 text-rose-200 text-xs flex items-center gap-2 shadow-sm">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Target Application & Execution Controller Card (Velvet Indigo) */}
      <Card variant="velvet" className="p-6 sm:p-8 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-white/10">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-white/10 border border-white/20 flex items-center justify-center text-white shrink-0 shadow-inner">
              <Globe className="w-6 h-6 text-purple-300" />
            </div>
            <div className="min-w-0 max-w-full">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h3 className="font-extrabold text-lg text-white truncate max-w-xs sm:max-w-md">
                  {selectedApp ? (selectedApp.name || selectedApp.url) : 'Select Application'}
                </h3>
                {selectedApp?.version && (
                  <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-white/15 text-purple-300 border border-white/20">
                    V{selectedApp.version}
                  </span>
                )}
              </div>
              <p className="text-xs font-mono text-slate-300 mt-1 truncate max-w-xs sm:max-w-md break-all" title={selectedApp?.url}>
                Target URL: <span className="text-white font-medium">{selectedApp?.url || '—'}</span>
              </p>
            </div>
          </div>

          {/* Mode Switcher & Execution Action */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="flex items-center gap-1.5 p-1 rounded-full bg-black/30 border border-white/10 text-xs">
              <button
                type="button"
                onClick={() => setOnlyQaoaSelected(true)}
                disabled={isRunning}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full font-semibold transition-all cursor-pointer ${
                  onlyQaoaSelected
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Atom className="w-3.5 h-3.5" />
                <span>QAOA Selected ({qaoaSelectedCount})</span>
              </button>

              <button
                type="button"
                onClick={() => setOnlyQaoaSelected(false)}
                disabled={isRunning}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full font-semibold transition-all cursor-pointer ${
                  !onlyQaoaSelected
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Full Suite ({candidateCount})</span>
              </button>
            </div>

            <button
              onClick={handleRunTests}
              disabled={isRunning || !selectedAppId || candidateCount === 0}
              className="h-11 px-6 rounded-full bg-white hover:bg-slate-100 text-purple-950 font-extrabold text-xs tracking-wide uppercase shadow-lg flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-50"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-purple-950" />
                  <span>Executing Playwright...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-purple-950 text-purple-950" />
                  <span>Run Playwright Suite</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Live Telemetry Progress State */}
        {execution && (
          <div className="space-y-4 pt-1">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5 shrink-0">
                    {isRunning ? (
                      <>
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-purple-400" />
                      </>
                    ) : (
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-white/50" />
                    )}
                  </span>
                  <h3 className="font-bold text-sm text-white">
                    Execution Session #{execution.id}
                  </h3>
                  <StatusBadge status={execution.status} size="sm" />
                </div>
                <p className="text-xs font-mono text-purple-200 mt-1 truncate max-w-xs sm:max-w-md break-all">
                  Active Endpoint: <span className="text-white font-medium" title={execution.current_url || selectedApp?.url}>{execution.current_url || selectedApp?.url}</span>
                </p>
              </div>

              <div className="text-right">
                <span className="text-2xl font-black font-mono text-white">
                  {progressPercent}%
                </span>
                <span className="block text-[11px] text-purple-200 font-medium">
                  {execution.stage || `${passedCount + failedCount}/${execution.total || candidateCount} completed`}
                </span>
              </div>
            </div>

            {/* Glowing Progress bar */}
            <div className="w-full bg-black/40 rounded-full h-2.5 overflow-hidden border border-white/10">
              <div
                className="bg-gradient-to-r from-purple-400 to-indigo-400 h-2.5 rounded-full transition-all duration-300 shadow-[0_0_12px_rgba(168,85,247,0.6)]"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            {/* Live activity ticker */}
            <div className="p-3.5 rounded-2xl bg-black/30 border border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
              <span className="text-slate-300 flex items-center gap-2 font-medium">
                <Radio className="w-3.5 h-3.5 text-purple-400 animate-pulse shrink-0" />
                <span>Running Test:</span>
                <strong className="text-white truncate">{execution.current_test || 'Idle — Ready'}</strong>
              </span>
              <span className="text-[11px] font-mono text-slate-300 flex items-center gap-1.5 shrink-0">
                <Terminal className="w-3 h-3 text-purple-400" />
                <span>{execution.browser_status || 'Chromium Headless Ready'}</span>
              </span>
            </div>
          </div>
        )}
      </Card>

      {/* KPI Cards (Floating Midnight Glass) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-5 text-center rounded-2xl">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">Total Executed</span>
          <span className="text-3xl font-extrabold text-white">{results.length}</span>
        </Card>
        <Card className="p-5 text-center rounded-2xl">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">Passed Checks</span>
          <span className="text-3xl font-extrabold text-emerald-400">{passedCount}</span>
        </Card>
        <Card className="p-5 text-center rounded-2xl">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">Detected Defects</span>
          <span className={`text-3xl font-extrabold ${failedCount > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
            {failedCount}
          </span>
        </Card>
        <Card className="p-5 text-center rounded-2xl">
          <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block mb-1">Browser Runtime</span>
          <span className="text-3xl font-extrabold text-purple-300">{totalDuration.toFixed(1)}s</span>
        </Card>
      </div>

      {/* Results Log */}
      {results.length === 0 && !isRunning ? (
        <Card className="p-12 text-center rounded-[28px]">
          <EmptyState
            icon={Play}
            title="No tests executed yet"
            description="Select an application and click 'Run Playwright Suite' to execute automated verifications."
          />
        </Card>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Live Test Execution Log ({results.length})
            </h3>
            <span className="text-xs font-medium text-slate-400">
              {passedCount} passed • {failedCount} failed
            </span>
          </div>

          <div className="space-y-3">
            {results.map((r) => {
              const isPassed = r.status === 'passed';

              return (
                <Card
                  key={r.id}
                  className={`p-5 transition-all border-l-4 rounded-2xl ${
                    isPassed ? 'border-l-emerald-500' : 'border-l-rose-500'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="mt-0.5 shrink-0">
                        {isPassed ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <XCircle className="w-5 h-5 text-rose-400" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-xs font-bold text-purple-300 px-2 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/20">
                            {r.test_id || `ID #${r.test_case_id}`}
                          </span>
                          {r.failure_category && (
                            <span className="font-mono text-[10px] font-semibold text-rose-300 px-2 py-0.5 rounded-full bg-rose-950/60 border border-rose-800/50">
                              {r.failure_category}
                            </span>
                          )}
                          <h4 className="font-bold text-sm text-white truncate">
                            {r.test_name || 'Automated Step Execution'}
                          </h4>
                        </div>
                        {r.error_message && (
                          <p className="text-xs text-rose-300 font-mono mt-2 leading-snug bg-rose-950/30 p-3 rounded-xl border border-rose-500/30">
                            {r.error_message}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 sm:self-center">
                      <span className="font-mono text-xs text-slate-400 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-purple-400" />
                        {(r.duration_ms / 1000).toFixed(2)}s
                      </span>
                      {r.screenshot_path ? (
                        <button
                          onClick={() => setSelectedScreenshot(r.screenshot_path)}
                          className="px-3 py-1 rounded-full bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 text-purple-300 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
                        >
                          <ImageIcon className="w-3.5 h-3.5" />
                          <span>Screenshot</span>
                        </button>
                      ) : (r.status === 'failed' || r.status === 'error') ? (
                        <span className="text-[11px] text-slate-500 italic px-1">
                          No snapshot
                        </span>
                      ) : null}
                      <StatusBadge status={r.status} size="sm" />
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Screenshot Preview Modal */}
      {selectedScreenshot && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
          onClick={() => setSelectedScreenshot(null)}
        >
          <div
            className="relative max-w-4xl w-full bg-[#0F172A] border border-white/15 rounded-3xl p-6 shadow-2xl overflow-hidden space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="font-extrabold text-base text-white flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-purple-400" />
                <span>Playwright Failure DOM Snapshot</span>
              </h3>
              <button
                onClick={() => setSelectedScreenshot(null)}
                className="p-1 rounded-full hover:bg-white/10 text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-2 max-h-[75vh] overflow-auto flex items-center justify-center bg-black/40 rounded-2xl border border-white/10">
              <img
                src={selectedScreenshot}
                alt="Test Failure DOM capture"
                className="rounded-xl border border-white/10 shadow-md max-w-full"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
