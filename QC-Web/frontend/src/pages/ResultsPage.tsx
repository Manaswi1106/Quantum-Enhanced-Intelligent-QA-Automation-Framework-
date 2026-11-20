import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  Printer,
  Clock,
  Image as ImageIcon,
  X,
  ShieldAlert,
  ShieldCheck,
  FileText,
  Copy,
  Check,
  Download,
  GitBranch,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { api } from '../services/api';

export default function ResultsPage() {
  const navigate = useNavigate();
  const [results, setResults] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScreenshot, setSelectedScreenshot] = useState<string | null>(null);

  // Developer Report Modal
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportMarkdown, setReportMarkdown] = useState<string>('');
  const [loadingReport, setLoadingReport] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true);
        const data = await api.getResults();
        setResults(data);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch regression results.');
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
  }, []);

  const total = results?.total_tests ?? 0;
  const passed = results?.passed ?? results?.passed_count ?? 0;
  const failed = results?.failed ?? results?.failed_count ?? 0;
  const skipped = results?.skipped ?? 0;
  const executionTimeMs = results?.execution_time_ms ?? 0;
  const failures = results?.blocking_failures ?? results?.failed_tests ?? [];
  const recommendations = results?.recommendations ?? [];

  const detectedDefects = results?.detected_defects ?? failures.filter((f: any) => !f.failure_category || f.failure_category === 'APPLICATION_FAILURE' || f.failure_category === 'ASSERTION_FAILURE').length;
  const totalCandidates = results?.total_candidates ?? total;
  const optimizedTests = results?.optimized_tests ?? null;
  const reductionPercent = results?.reduction_percent ?? null;
  const appFailures = results?.application_failures ?? 0;
  const assertionFailures = results?.assertion_failures ?? 0;
  const navFailures = results?.navigation_failures ?? 0;
  const envFailures = results?.environment_failures ?? 0;
  const execErrors = results?.execution_errors ?? 0;

  const successRate = total > 0 ? Math.round((passed / total) * 100) : 0;
  const isReady = failed === 0 && passed > 0;

  const handlePrint = () => {
    window.print();
  };

  const handleOpenDeveloperReport = async () => {
    setShowReportModal(true);
    setLoadingReport(true);
    try {
      const reportData = await api.getDeveloperReport();
      setReportMarkdown(reportData.report_markdown || 'No defect report generated.');
    } catch {
      // Fallback synthesis from current results
      let md = `# Regression Defect Report\n\n`;
      md += `**Generated**: ${new Date().toISOString()}\n`;
      md += `**Quality Score**: ${successRate}%\n`;
      md += `**Passed**: ${passed} | **Failed**: ${failed}\n\n`;
      if (failures.length > 0) {
        md += `## Blocking Defects\n\n`;
        failures.forEach((f: any, i: number) => {
          md += `### ${i + 1}. [${f.test_id || 'TC-FAIL'}] ${f.test_name}\n`;
          if (f.failure_category) md += `- **Classification**: \`${f.failure_category}\`\n`;
          md += `- **Error**: \`${f.error_message || 'Assertion rejected'}\`\n`;
          if (f.duration_ms) md += `- **Duration**: ${f.duration_ms}ms\n`;
          md += `- **Evidence**: ${f.screenshot_path ? 'DOM Screenshot captured' : `Screenshot unavailable (${f.failure_category || 'Not captured'})`}\n`;
          md += `\n`;
        });
      }
      setReportMarkdown(md);
    } finally {
      setLoadingReport(false);
    }
  };

  const handleCopyReport = () => {
    navigator.clipboard.writeText(reportMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadReport = () => {
    const blob = new Blob([reportMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qcweb-defect-report-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/15 text-purple-300 text-[11px] font-semibold uppercase tracking-wider mb-2 backdrop-blur-md">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            <span>Decision Analytics</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Regression Verification Analytics
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Production release decision analysis powered by Playwright verification findings.
          </p>
        </div>

        <div className="flex items-center gap-3 print:hidden">
          <button
            onClick={handleOpenDeveloperReport}
            className="h-11 px-5 rounded-full card-porcelain hover:bg-white/10 text-purple-300 hover:text-white text-xs font-bold border border-white/10 shadow-xs flex items-center gap-2 cursor-pointer transition-all"
          >
            <FileText className="w-4 h-4 text-purple-400" />
            <span>Developer Bug Report</span>
          </button>

          <button
            onClick={handlePrint}
            className="h-11 px-4 rounded-full card-porcelain hover:bg-white/10 text-slate-400 hover:text-white text-xs font-semibold border border-white/10 shadow-xs flex items-center gap-2 cursor-pointer transition-all"
          >
            <Printer className="w-4 h-4 text-slate-400" />
            <span>Print Report</span>
          </button>

          {failed > 0 && (
            <button
              onClick={() => navigate('/applications')}
              className="h-11 px-6 rounded-full btn-velvet text-xs font-bold tracking-wide uppercase flex items-center gap-2 cursor-pointer transition-all"
            >
              <GitBranch className="w-4 h-4" />
              <span>Test V2 Fix</span>
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <LoadingState message="Aggregating regression verification metrics from Supabase..." />
      ) : error ? (
        <div className="p-5 rounded-2xl bg-rose-950/40 border border-rose-800/40 text-rose-300 text-sm">
          {error}
        </div>
      ) : !results || total === 0 ? (
        <Card variant="porcelain" className="p-12 text-center">
          <EmptyState
            icon={CheckCircle2}
            title="No evaluation data available yet"
            description="Execute test suites via the Execution page to synthesize release readiness evaluations."
          />
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Readiness Decision Banner */}
          <Card
            variant={isReady ? 'porcelain' : 'velvet'}
            className={`p-7 sm:p-8 rounded-[32px] transition-all ${
              isReady ? 'border-2 border-emerald-500/40 bg-emerald-950/20' : ''
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
              <div className="flex items-start gap-4">
                <div
                  className={`w-14 h-14 rounded-2xl flex items-center justify-center shrink-0 shadow-md ${
                    isReady
                      ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700/50'
                      : 'bg-white/15 text-white border border-white/20'
                  }`}
                >
                  {isReady ? (
                    <ShieldCheck className="w-8 h-8" />
                  ) : (
                    <ShieldAlert className="w-8 h-8 text-rose-300" />
                  )}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[11px] font-bold uppercase tracking-wider px-3 py-0.5 rounded-full ${
                        isReady
                          ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
                          : 'bg-white/20 text-rose-200 border border-white/30'
                      }`}
                    >
                      {isReady ? 'READY TO LAUNCH' : 'CHANGES REQUIRED'}
                    </span>
                  </div>

                  <h2 className="text-xl sm:text-2xl font-black mt-2 tracking-tight text-white">
                    {isReady
                      ? 'All Regression Tests Passed — Production Safe'
                      : `${failed} Blocking Regression Defect${failed > 1 ? 's' : ''} Detected`}
                  </h2>

                  <p className={`text-xs sm:text-sm mt-1 max-w-xl ${isReady ? 'text-slate-300' : 'text-slate-200'}`}>
                    {isReady
                      ? 'No unexpected mutations or client-side validation breakdowns were detected across the analyzed test suite.'
                      : 'Playwright encountered assertion failures. Review the defect logs, DOM snapshots, and developer bug report below.'}
                  </p>
                </div>
              </div>

              <div className={`sm:text-right shrink-0 p-4 rounded-2xl ${isReady ? 'bg-emerald-950/30 border border-emerald-800/30' : 'bg-black/30 border border-white/10'}`}>
                <span className="text-xs font-bold uppercase tracking-wider block text-slate-400">
                  Quality Score
                </span>
                <span
                  className={`text-3xl sm:text-4xl font-extrabold font-mono tracking-tight ${
                    isReady ? 'text-emerald-400' : 'text-white'
                  }`}
                >
                  {successRate}%
                </span>
                <span className="text-[11px] font-mono block mt-0.5 text-slate-400">
                  {passed}/{total} verifications
                </span>
              </div>
            </div>
          </Card>

          {/* Research Pipeline Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <Card variant="porcelain" className="p-4 text-center">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Candidate Tests</span>
              <span className="text-2xl font-extrabold text-white">{totalCandidates}</span>
            </Card>

            <Card variant="porcelain" className="p-4 text-center">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">QAOA Optimized</span>
              <span className="text-2xl font-extrabold text-purple-300">
                {optimizedTests !== null ? optimizedTests : total}
              </span>
              {reductionPercent !== null && (
                <span className="text-[10px] text-emerald-400 block font-mono font-bold mt-0.5">
                  -{reductionPercent}% reduction
                </span>
              )}
            </Card>

            <Card variant="porcelain" className="p-4 text-center">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Executed Tests</span>
              <span className="text-2xl font-extrabold text-white">{total}</span>
            </Card>

            <Card variant="porcelain" className="p-4 text-center">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Passed Checks</span>
              <span className="text-2xl font-extrabold text-emerald-400">{passed}</span>
            </Card>

            <Card variant="porcelain" className="p-4 text-center">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Application Defects</span>
              <span className={`text-2xl font-extrabold ${detectedDefects > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
                {detectedDefects}
              </span>
              <span className="text-[9px] text-slate-500 block uppercase mt-0.5">True Defects</span>
            </Card>

            <Card variant="porcelain" className="p-4 text-center">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">Total Runtime</span>
              <span className="text-2xl font-extrabold text-purple-400">
                {(executionTimeMs / 1000).toFixed(2)}s
              </span>
            </Card>
          </div>

          {/* Failure Classification Breakdown if failures exist */}
          {failed > 0 && (
            <div className="p-4 rounded-2xl bg-black/40 border border-white/10 flex flex-wrap items-center gap-4 text-xs font-mono">
              <span className="text-slate-400 font-bold uppercase text-[10px]">Failure Classification:</span>
              <span className="text-rose-300">App Failures: <strong className="text-white">{appFailures}</strong></span>
              <span className="text-amber-300">Assertion Failures: <strong className="text-white">{assertionFailures}</strong></span>
              <span className="text-blue-300">Navigation Failures: <strong className="text-white">{navFailures}</strong></span>
              <span className="text-purple-300">Environment Failures: <strong className="text-white">{envFailures}</strong></span>
              <span className="text-slate-300">Execution Errors: <strong className="text-white">{execErrors}</strong></span>
            </div>
          )}

          {/* Visual Distribution Bar */}
          <Card variant="porcelain" className="p-6 space-y-3">
            <div className="flex items-center justify-between text-xs font-bold text-slate-200">
              <span>Test Suite Status Distribution</span>
              <span className="text-purple-400">{successRate}% Pass Success</span>
            </div>

            <div className="w-full bg-slate-800/80 rounded-full h-3 overflow-hidden flex border border-white/10">
              <div
                className="bg-emerald-500 h-full transition-all duration-300"
                style={{ width: `${(passed / total) * 100}%` }}
                title={`Passed: ${passed}`}
              />
              <div
                className="bg-rose-500 h-full transition-all duration-300"
                style={{ width: `${(failed / total) * 100}%` }}
                title={`Failed: ${failed}`}
              />
              <div
                className="bg-slate-600 h-full transition-all duration-300"
                style={{ width: `${(skipped / total) * 100}%` }}
                title={`Skipped: ${skipped}`}
              />
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-1">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                Passed ({passed})
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                Failed ({failed})
              </span>
              {skipped > 0 && (
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-slate-600" />
                  Skipped ({skipped})
                </span>
              )}
            </div>
          </Card>

          {/* Detected Defects List */}
          {failures.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2 text-rose-400 font-bold text-sm">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Detected Regression Defects ({failures.length})</span>
                </div>
                <button
                  onClick={handleOpenDeveloperReport}
                  className="text-xs font-bold text-purple-400 hover:text-purple-300 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Generate Report for Devs</span>
                </button>
              </div>

              <div className="space-y-3">
                {failures.map((f: any, idx: number) => (
                  <Card
                    key={f.id || idx}
                    variant="porcelain"
                    className="p-5 sm:p-6 border-l-4 border-l-rose-500 space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs font-bold text-rose-300 bg-rose-950/60 px-2 py-0.5 rounded-md border border-rose-800/50">
                          {f.test_id || `TC-FAIL-${idx + 1}`}
                        </span>
                        {f.failure_category && (
                          <span className="font-mono text-[10px] font-semibold text-purple-300 bg-purple-950/60 px-2 py-0.5 rounded-md border border-purple-800/50">
                            {f.failure_category}
                          </span>
                        )}
                        <h4 className="font-extrabold text-sm text-white">
                          {f.test_name || 'Regression Failure'}
                        </h4>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {f.duration_ms && (
                          <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-purple-400" />
                            {f.duration_ms}ms
                          </span>
                        )}
                        {f.screenshot_path ? (
                          <button
                            onClick={() => setSelectedScreenshot(f.screenshot_path)}
                            className="px-3 py-1 rounded-full bg-purple-900/30 hover:bg-purple-900/50 border border-purple-700/50 text-purple-300 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
                          >
                            <ImageIcon className="w-3.5 h-3.5" />
                            <span>View DOM Snapshot</span>
                          </button>
                        ) : (
                          <span className="text-[11px] text-slate-500 italic px-2">
                            Screenshot unavailable
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-800/40 text-rose-200 text-xs font-mono leading-relaxed">
                      {f.error_message || 'Assertion rejected during step execution.'}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Actionable Engineering Recommendations */}
          {recommendations.length > 0 && (
            <Card variant="porcelain" className="p-6 sm:p-7 space-y-4">
              <div className="flex items-center gap-2 text-white">
                <Lightbulb className="w-4 h-4 text-purple-400" />
                <h3 className="font-extrabold text-sm">Actionable Defect Recommendations</h3>
              </div>

              <ul className="space-y-2 text-xs text-slate-300 pl-1 font-mono">
                {recommendations.map((rec: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2.5">
                    <span className="w-2 h-2 rounded-full bg-purple-400 mt-1 shrink-0" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      )}

      {/* Developer Bug Report Modal */}
      {showReportModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md"
          onClick={() => setShowReportModal(false)}
        >
          <div
            className="relative max-w-3xl w-full bg-slate-900 border border-white/10 rounded-3xl p-6 shadow-2xl overflow-hidden space-y-4 text-white"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-purple-400" />
                <h3 className="font-extrabold text-base text-white">
                  Developer Bug Report (Ready to Share)
                </h3>
              </div>
              <button
                onClick={() => setShowReportModal(false)}
                className="p-1 rounded-full hover:bg-white/10 text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingReport ? (
              <div className="py-12 text-center text-purple-300 text-xs font-mono">
                Formatting defect report...
              </div>
            ) : (
              <>
                <div className="max-h-[60vh] overflow-auto p-4 bg-slate-950/80 rounded-2xl border border-white/10">
                  <pre className="text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {reportMarkdown}
                  </pre>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    onClick={handleCopyReport}
                    className="h-10 px-4 rounded-full card-porcelain hover:bg-white/10 text-purple-300 text-xs font-bold border border-white/10 flex items-center gap-2 cursor-pointer transition-all"
                  >
                    {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    <span>{copied ? 'Copied to Clipboard!' : 'Copy Markdown'}</span>
                  </button>

                  <button
                    onClick={handleDownloadReport}
                    className="h-10 px-5 rounded-full btn-velvet text-xs font-bold flex items-center gap-2 cursor-pointer transition-all"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Report (.md)</span>
                  </button>
                </div>
              </>
            )}
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
            className="relative max-w-4xl w-full bg-slate-900 border border-white/10 rounded-3xl p-6 shadow-2xl overflow-hidden space-y-4 text-white"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="font-extrabold text-base text-white flex items-center gap-2">
                <ImageIcon className="w-4 h-4 text-purple-400" />
                <span>Defect Failure Screenshot (DOM Snapshot)</span>
              </h3>
              <button
                onClick={() => setSelectedScreenshot(null)}
                className="p-1 rounded-full hover:bg-white/10 text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-2 max-h-[75vh] overflow-auto flex items-center justify-center bg-slate-950/80 rounded-2xl border border-white/10">
              <img
                src={selectedScreenshot}
                alt="Defect Failure capture"
                className="rounded-xl border border-white/10 shadow-md max-w-full"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
