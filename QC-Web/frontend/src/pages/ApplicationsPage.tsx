import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Globe,
  Plus,
  ExternalLink,
  Layers,
  X,
  Play,
  Atom,
  BarChart3,
  GitBranch,
  RefreshCw,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { StatusBadge } from '../components/ui/StatusBadge';
import { api } from '../services/api';

export function ApplicationsPage() {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Retry & Delete state
  const [retryingAppId, setRetryingAppId] = useState<number | null>(null);
  const [deletingAppId, setDeletingAppId] = useState<number | null>(null);

  // Analyze Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeStage, setAnalyzeStage] = useState('Crawling DOM...');
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  // Version 2 Modal state
  const [isV2ModalOpen, setIsV2ModalOpen] = useState(false);
  const [v2TargetApp, setV2TargetApp] = useState<any | null>(null);
  const [v2Url, setV2Url] = useState('');
  const [isCreatingV2, setIsCreatingV2] = useState(false);

  const handleRetryAnalysis = async (app: any) => {
    if (!app || retryingAppId) return;
    try {
      setRetryingAppId(app.id);
      await api.analyzeUrl(app.url, true);
      await fetchApplications();
    } catch (err: any) {
      alert(`Retry analysis failed for ${app.url}: ${err.message}`);
    } finally {
      setRetryingAppId(null);
    }
  };

  const handleDeleteApp = async (appId: number, appName: string) => {
    if (!window.confirm(`Are you sure you want to delete application "${appName}"? This will remove its discovered endpoints.`)) {
      return;
    }
    try {
      setDeletingAppId(appId);
      await api.deleteApplication(appId);
      await fetchApplications();
    } catch (err: any) {
      alert(`Failed to delete application: ${err.message}`);
    } finally {
      setDeletingAppId(null);
    }
  };

  const fetchApplications = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getApplications();
      setApplications(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch applications from Supabase.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    try {
      setIsAnalyzing(true);
      setAnalyzeError(null);
      setAnalyzeStage('Launching Chromium crawler...');

      const stageTimer1 = setTimeout(() => setAnalyzeStage('Discovering routes & form elements...'), 2500);
      const stageTimer2 = setTimeout(() => setAnalyzeStage('Synthesizing structured elements...'), 6000);

      await api.analyzeUrl(url.trim());
      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);

      setIsModalOpen(false);
      setUrl('');
      await fetchApplications();
    } catch (err: any) {
      setAnalyzeError(err.message || 'Failed to analyze URL. Please check connection and URL format.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleOpenV2Modal = (app: any) => {
    setV2TargetApp(app);
    setV2Url(app.url);
    setIsV2ModalOpen(true);
  };

  const handleCreateV2 = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!v2TargetApp || !v2Url.trim()) return;

    try {
      setIsCreatingV2(true);
      await api.createApplicationVersion({
        baseline_app_id: v2TargetApp.id,
        version_label: 'v2',
        new_url: v2Url.trim(),
      });
      setIsV2ModalOpen(false);
      await fetchApplications();
      navigate(`/test-cases?app_id=${v2TargetApp.id}`);
    } catch (err: any) {
      alert(`Failed to register Version 2: ${err.message}`);
    } finally {
      setIsCreatingV2(false);
    }
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Target Applications
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Registered web targets, autonomous route maps, and interactive UI surfaces in Supabase.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="h-12 px-6 rounded-full btn-burgundy text-white text-xs font-bold tracking-wide uppercase shadow-lg flex items-center gap-2 cursor-pointer transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Analyze New Website</span>
        </button>
      </div>

      {/* Summary Filter / Counters */}
      {!loading && applications.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
          <div className="px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 text-slate-300">
            Total Registered: <strong className="text-white">{applications.length}</strong>
          </div>
          <div className="px-3.5 py-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
            Active Targets: <strong className="text-white">{applications.filter((a) => a.status === 'active').length}</strong>
          </div>
          {applications.some((a) => a.status === 'limited_discovery') && (
            <div className="px-3.5 py-1.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300">
              Limited Discovery: <strong className="text-white">{applications.filter((a) => a.status === 'limited_discovery').length}</strong>
            </div>
          )}
          {applications.some((a) => a.status === 'failed' || a.status === 'error') && (
            <div className="px-3.5 py-1.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300">
              Failed Analyses: <strong className="text-white">{applications.filter((a) => a.status === 'failed' || a.status === 'error').length}</strong>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <LoadingState message="Loading target applications from Supabase..." />
      ) : error ? (
        <Card className="p-8 text-center text-rose-300 bg-rose-950/20 border border-rose-500/30 text-sm rounded-[28px]">
          {error}
        </Card>
      ) : applications.length === 0 ? (
        <Card className="p-12 text-center rounded-[28px]">
          <EmptyState
            icon={Globe}
            title="No applications analyzed yet"
            description="Enter a website URL to initiate autonomous Playwright crawling and AI test generation."
            action={
              <button
                onClick={() => setIsModalOpen(true)}
                className="h-11 px-6 rounded-full btn-burgundy text-white text-xs font-bold uppercase cursor-pointer shadow-md"
              >
                Analyze Target Website
              </button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-6">
            {applications.map((app) => {
              const analysis = app.analysis_data || {};
              const pages = analysis.pages || [];
              const buttons = analysis.buttons || [];
              const inputs = analysis.inputs || [];
              const forms = analysis.forms || [];
              const isFailed = app.status === 'failed' || app.status === 'error';
              const isAnalyzingNow = app.status === 'analyzing';
              const isLimited = app.status === 'limited_discovery';
              const isUsable = app.status === 'active' || (isLimited && app.discovered_elements > 0);
              const isRetryingThis = retryingAppId === app.id;
              const isDeletingThis = deletingAppId === app.id;

              return (
                <Card
                  key={app.id}
                  className={`p-7 sm:p-8 rounded-[28px] space-y-6 transition-all ${
                    isFailed ? 'border-rose-500/30 bg-rose-950/10' : ''
                  }`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-white/10">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <h3 className="text-xl font-black text-white tracking-tight">
                          {app.name || app.url}
                        </h3>
                        <StatusBadge status={app.status} size="sm" />
                        <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">
                          App #{app.id}
                        </span>
                        {analysis.error_category && (
                          <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/30">
                            {analysis.error_category}
                          </span>
                        )}
                      </div>
                      <a
                        href={app.url}
                        target="_blank"
                        rel="noreferrer"
                        title={app.url}
                        className="inline-flex items-center gap-1.5 text-xs font-mono text-purple-300 hover:text-purple-200 hover:underline max-w-full sm:max-w-md md:max-w-lg truncate break-all"
                      >
                        <span className="truncate">{app.url}</span>
                        <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                      </a>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {/* Retry Analysis for failed or limited apps */}
                      {(isFailed || isLimited) && (
                        <button
                          onClick={() => handleRetryAnalysis(app)}
                          disabled={isRetryingThis || isAnalyzingNow}
                          className="h-9 px-4 rounded-full bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/40 text-purple-200 text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs disabled:opacity-50"
                          title="Rerun autonomous Playwright discovery on this website"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isRetryingThis ? 'animate-spin' : ''}`} />
                          <span>{isRetryingThis ? 'Retrying...' : 'Retry Discovery'}</span>
                        </button>
                      )}

                      <button
                        onClick={() => navigate(`/test-cases?app_id=${app.id}`)}
                        disabled={!isUsable}
                        className="h-9 px-4 rounded-full btn-pill-outline text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed"
                        title={!isUsable ? 'Complete website discovery and generate valid tests first.' : 'View candidate test cases'}
                      >
                        <Layers className="w-3.5 h-3.5 text-purple-400" />
                        <span>View Tests</span>
                      </button>

                      <button
                        onClick={() => navigate(`/optimization?app_id=${app.id}`)}
                        disabled={!isUsable}
                        className="h-9 px-4 rounded-full btn-pill-outline text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed"
                        title={!isUsable ? 'Complete website discovery and generate valid tests first.' : 'Run QAOA Circuit'}
                      >
                        <Atom className="w-3.5 h-3.5 text-purple-400" />
                        <span>Run QAOA</span>
                      </button>

                      <button
                        onClick={() => navigate(`/execution?app_id=${app.id}`)}
                        disabled={!isUsable}
                        className="h-9 px-4 rounded-full btn-burgundy text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors shadow-xs disabled:opacity-40 disabled:cursor-not-allowed"
                        title={!isUsable ? 'Complete website discovery and generate valid tests first.' : 'Execute test suite'}
                      >
                        <Play className="w-3.5 h-3.5 fill-white" />
                        <span>Execute Suite</span>
                      </button>

                      <button
                        onClick={() => navigate(`/results?app_id=${app.id}`)}
                        className="h-9 px-3.5 rounded-full btn-pill-outline text-slate-300 text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors"
                        title="View historical results"
                      >
                        <BarChart3 className="w-3.5 h-3.5" />
                        <span>Results</span>
                      </button>

                      <button
                        onClick={() => handleOpenV2Modal(app)}
                        disabled={!isUsable}
                        className="h-9 px-3.5 rounded-full bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-500/30 text-emerald-300 text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        title={!isUsable ? 'Complete website discovery first.' : 'Register new version'}
                      >
                        <GitBranch className="w-3.5 h-3.5" />
                        <span>+ New Version</span>
                      </button>

                      <button
                        onClick={() => handleDeleteApp(app.id, app.name || app.url)}
                        disabled={isDeletingThis}
                        className="h-9 px-3 rounded-full hover:bg-rose-950/50 border border-white/10 hover:border-rose-500/40 text-slate-400 hover:text-rose-300 text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors"
                        title="Delete application record (with confirmation)"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Informational Banner for Failed or Limited Discovery Targets */}
                  {isFailed && (
                    <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/30 flex items-start gap-3 text-xs text-rose-200">
                      <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        <strong className="block font-bold text-rose-300">
                          Website Discovery Failed {analysis.error_category ? `(${analysis.error_category})` : ''}
                        </strong>
                        <p className="text-slate-300 leading-relaxed font-mono">
                          {analysis.error || analysis.discovery_notes || 'Target website was unreachable during Playwright navigation. QAOA optimization and Playwright execution are disabled until valid discovery succeeds.'}
                        </p>
                      </div>
                    </div>
                  )}

                  {isLimited && (
                    <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-500/30 flex items-start gap-3 text-xs text-amber-200">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        <strong className="block font-bold text-amber-300">Limited Website Discovery</strong>
                        <p className="text-slate-300 leading-relaxed">
                          {analysis.discovery_notes || 'The crawler detected restricted automated access or minimal DOM structure. You can retry discovery or test basic connectivity.'}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Metrics Bar */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                      <span className="text-slate-400 block text-[10px] uppercase">Pages Discovered</span>
                      <strong className="text-xl font-bold text-white">{pages.length || app.discovered_pages || 0}</strong>
                    </div>

                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                      <span className="text-slate-400 block text-[10px] uppercase">Interactive Elements</span>
                      <strong className="text-xl font-bold text-purple-300">{app.discovered_elements || 0}</strong>
                    </div>

                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                      <span className="text-slate-400 block text-[10px] uppercase">Buttons & CTA</span>
                      <strong className="text-xl font-bold text-white">{buttons.length}</strong>
                    </div>

                    <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                      <span className="text-slate-400 block text-[10px] uppercase">Inputs & Forms</span>
                      <strong className="text-xl font-bold text-white">{inputs.length} / {forms.length}</strong>
                    </div>
                  </div>

                  {/* Discovered Endpoints Preview */}
                  {pages.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
                        Discovered Routes & Endpoints ({pages.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                        {pages.map((p: any, idx: number) => {
                          const displayPath = p.path || p.url;
                          return (
                            <span
                              key={idx}
                              title={displayPath}
                              className="px-2.5 py-1 rounded-full bg-white/5 text-slate-300 border border-white/10 text-[11px] font-mono max-w-xs truncate"
                            >
                              {displayPath}
                            </span>
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

      {/* Analyze Website Modal */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md"
          onClick={() => !isAnalyzing && setIsModalOpen(false)}
        >
          <div
            className="relative max-w-lg w-full bg-[#0F172A] border border-white/15 rounded-[28px] p-6 shadow-2xl space-y-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="font-extrabold text-lg text-white flex items-center gap-2">
                <Globe className="w-5 h-5 text-purple-400" />
                <span>Analyze New Web Target</span>
              </h3>
              <button
                onClick={() => !isAnalyzing && setIsModalOpen(false)}
                disabled={isAnalyzing}
                className="p-1.5 rounded-full hover:bg-white/10 text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Enter the root URL of any accessible web application. Playwright will crawl internal routes, map interactive inputs and buttons, and store the discovered structure in Supabase.
            </p>

            <form onSubmit={handleAnalyze} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                  Website URL
                </label>
                <input
                  type="url"
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com or any web app URL"
                  disabled={isAnalyzing}
                  className="w-full h-11 px-4 bg-[#0B0F19] border border-white/15 rounded-full text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              {isAnalyzing && (
                <div className="p-3 rounded-2xl bg-purple-950/30 border border-purple-500/30 flex items-center gap-3 text-xs text-purple-200">
                  <div className="w-3.5 h-3.5 border-2 border-purple-400 border-t-transparent rounded-full animate-spin shrink-0" />
                  <span className="font-mono">{analyzeStage}</span>
                </div>
              )}

              {analyzeError && (
                <div className="p-3 rounded-2xl bg-rose-950/30 border border-rose-500/30 text-rose-200 text-xs">
                  {analyzeError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  disabled={isAnalyzing}
                  className="h-10 px-5 rounded-full btn-pill-outline text-xs font-bold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAnalyzing || !url.trim()}
                  className="h-10 px-6 rounded-full btn-burgundy text-white text-xs font-bold flex items-center gap-2 cursor-pointer shadow-md"
                >
                  {isAnalyzing ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Crawling...</span>
                    </>
                  ) : (
                    <span>Start Analysis</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Version 2 Regression Modal */}
      {isV2ModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md"
          onClick={() => !isCreatingV2 && setIsV2ModalOpen(false)}
        >
          <div
            className="relative max-w-lg w-full bg-[#0F172A] border border-white/15 rounded-[28px] p-6 shadow-2xl space-y-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <h3 className="font-extrabold text-lg text-white flex items-center gap-2">
                <GitBranch className="w-5 h-5 text-emerald-400" />
                <span>New Application Version (V2 Regression)</span>
              </h3>
              <button
                onClick={() => !isCreatingV2 && setIsV2ModalOpen(false)}
                disabled={isCreatingV2}
                className="p-1.5 rounded-full hover:bg-white/10 text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Register a new version of <strong>{v2TargetApp?.name || v2TargetApp?.url}</strong>. QC-Web automatically retains and elevates previously failed regression tests as high-priority candidates for the QAOA optimization cycle.
            </p>

            <form onSubmit={handleCreateV2} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                  Version 2 Target URL
                </label>
                <input
                  type="url"
                  required
                  value={v2Url}
                  onChange={(e) => setV2Url(e.target.value)}
                  placeholder="https://example.com/v2 or updated URL"
                  disabled={isCreatingV2}
                  className="w-full h-11 px-4 bg-[#0B0F19] border border-white/15 rounded-full text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsV2ModalOpen(false)}
                  disabled={isCreatingV2}
                  className="h-10 px-5 rounded-full btn-pill-outline text-xs font-bold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingV2 || !v2Url.trim()}
                  className="h-10 px-6 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-2 cursor-pointer shadow-md"
                >
                  {isCreatingV2 ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Ingesting V2...</span>
                    </>
                  ) : (
                    <span>Register V2 Target</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default ApplicationsPage;
