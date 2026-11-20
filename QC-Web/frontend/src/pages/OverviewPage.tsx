import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Globe,
  Search,
  FileCheck,
  Atom,
  CheckCircle2,
  Sparkles,
  Layers,
  ArrowRight,
  AlertTriangle,
  Cpu,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { StatusBadge } from '../components/ui/StatusBadge';
import { api } from '../services/api';

export function OverviewPage() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeStage, setAnalyzeStage] = useState('Initializing Playwright crawler...');
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const [aiStatus, setAiStatus] = useState<{ configured: boolean; provider: string | null; message: string }>({
    configured: false,
    provider: null,
    message: '',
  });

  const [metrics, setMetrics] = useState({
    applications: 0,
    generated_tests: 0,
    executions: 0,
    optimizations: 0,
    detected_defects: 0,
    pass_rate: 0,
  });

  const [recentApps, setRecentApps] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      try {
        const [metricsData, appsData, aiData] = await Promise.all([
          api.getOverviewMetrics().catch(() => ({
            applications: 0,
            generated_tests: 0,
            executions: 0,
            optimizations: 0,
            detected_defects: 0,
            pass_rate: 0,
          })),
          api.getApplications().catch(() => []),
          api.getAIStatus().catch(() => ({ configured: false, provider: null, message: '' })),
        ]);
        if (mounted) {
          setMetrics(metricsData);
          setRecentApps(appsData.slice(0, 3));
          setAiStatus(aiData);
        }
      } catch (err) {
        console.error('Failed to load overview data:', err);
      }
    };
    fetchData();
    return () => {
      mounted = false;
    };
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    const timers: any[] = [];
    try {
      setIsAnalyzing(true);
      setAnalyzeError(null);
      setAnalyzeStage('Launching headless Chromium crawler...');

      timers.push(setTimeout(() => setAnalyzeStage('Navigating to target and loading DOM...'), 3000));
      timers.push(setTimeout(() => setAnalyzeStage('Discovering routes, navigation links & SPAs...'), 8000));
      timers.push(setTimeout(() => setAnalyzeStage('Crawling pages and extracting interactive elements...'), 16000));
      timers.push(setTimeout(() => setAnalyzeStage('Parsing forms, inputs, buttons & state transitions...'), 24000));
      timers.push(setTimeout(() => setAnalyzeStage('Finalizing discovery and persisting structure (almost done)...'), 32000));

      const appResult = await api.analyzeUrl(url.trim());
      timers.forEach(clearTimeout);

      if (appResult && appResult.id) {
        navigate(`/applications`);
      } else {
        navigate('/applications');
      }
    } catch (err: any) {
      timers.forEach(clearTimeout);
      setAnalyzeError(err.message || 'Failed to analyze URL. Please ensure target website is accessible.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const workflowSteps = [
    {
      num: '01',
      title: 'ANALYZE',
      subtitle: 'Playwright Discovery',
      desc: 'Headless Chromium autonomously crawls routes, inputs, and interactive elements without hardcoded knowledge.',
      icon: Search,
    },
    {
      num: '02',
      title: 'SYNTHESIZE',
      subtitle: 'Real AI Test Generation',
      desc: 'Gemini or OpenAI parses discovered DOM elements to synthesize structured candidate regression scenarios.',
      icon: Sparkles,
    },
    {
      num: '03',
      title: 'PERSIST',
      subtitle: 'Supabase PostgreSQL',
      desc: 'Real tables store applications, routes, candidate tests, execution history, and regression versions.',
      icon: Layers,
    },
    {
      num: '04',
      title: 'FORMULATE',
      subtitle: 'QUBO Mathematical Model',
      desc: 'Formulates quadratic unconstrained binary optimization balancing risk, coverage, change impact, and budget.',
      icon: Cpu,
    },
    {
      num: '05',
      title: 'OPTIMIZE',
      subtitle: 'QAOA Circuit (Qiskit Aer)',
      desc: 'Simulates parameterized quantum alternating operator ansatz to sample the optimal regression test subset.',
      icon: Atom,
    },
    {
      num: '06',
      title: 'EXECUTE & VERIFY',
      subtitle: 'Playwright Execution & Reports',
      desc: 'Executes ONLY QAOA-selected tests, records real pass/fail evidence, and retains defects for V2 regression.',
      icon: CheckCircle2,
    },
  ];

  return (
    <div className="space-y-10 pb-16">
      {/* Top Tag & Hero Title */}
      <div className="text-center max-w-3xl mx-auto space-y-4 pt-4">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 border border-white/15 shadow-xs text-xs font-bold text-purple-300 tracking-wider uppercase backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
          <span>QC-Web V2 • Quantum-Assisted Regression Intelligence</span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.1]">
          Intelligent Web Regression <br />
          <span className="bg-gradient-to-r from-purple-400 via-indigo-300 to-purple-500 bg-clip-text text-transparent">
            Optimized with QAOA
          </span>
        </h1>

        <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Autonomous Playwright discovery, real AI test synthesis, and Qiskit Aer quantum circuit
          optimization. Test what matters without redundant execution overhead.
        </p>
      </div>

      {/* Primary Stable Card: Analyze Website */}
      <div className="max-w-3xl mx-auto">
        <div className="card-velvet p-7 sm:p-9 rounded-[32px] relative overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <div>
              <span className="text-[11px] font-mono uppercase tracking-widest text-purple-300/80 block mb-1">
                Step 01 • Application Ingestion
              </span>
              <h2 className="text-2xl font-black text-white tracking-tight">
                Analyze a Deployed Website
              </h2>
            </div>

            <div className="shrink-0">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${
                aiStatus.configured 
                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/40' 
                  : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
              }`}>
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI: {aiStatus.configured ? (aiStatus.provider?.toUpperCase() || 'Active') : 'Not Configured'}</span>
              </span>
            </div>
          </div>

          <p className="text-xs sm:text-sm text-slate-300 mb-6 leading-relaxed">
            Enter any accessible web application URL. Playwright launches headless Chromium to crawl all routes,
            extract interactive form elements, and synthesize regression tests with real AI.
          </p>

          <form onSubmit={handleAnalyze} className="space-y-4">
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <div className="relative flex-1 w-full">
                <Globe className="w-5 h-5 text-slate-400 absolute left-4.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="url"
                  required
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com or any deployed web URL"
                  disabled={isAnalyzing}
                  className="w-full h-13 pl-12 pr-4 bg-[#0F172A]/90 text-white placeholder-slate-500 rounded-full border border-white/20 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-purple-500 shadow-md"
                />
              </div>

              <button
                type="submit"
                disabled={isAnalyzing || !url.trim()}
                className="w-full sm:w-auto h-13 px-8 rounded-full btn-burgundy text-white font-bold text-sm tracking-wide shadow-lg flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-60 shrink-0"
              >
                {isAnalyzing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-purple-200" />
                    <span>Analyze Website</span>
                  </>
                )}
              </button>
            </div>

            {isAnalyzing && (
              <div className="p-3.5 rounded-2xl bg-white/10 border border-white/15 flex items-center gap-3 text-xs text-white">
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin shrink-0" />
                <span className="font-mono">{analyzeStage}</span>
              </div>
            )}

            {analyzeError && (
              <div className="p-3.5 rounded-2xl bg-rose-950/40 border border-rose-500/40 text-rose-200 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-300" />
                <span>{analyzeError}</span>
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Real Platform Telemetry from Supabase */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between px-2">
          <span className="text-xs font-mono uppercase tracking-widest text-slate-400 font-bold">
            Real-Time Platform Telemetry (Supabase PostgreSQL)
          </span>
          <span className="text-xs font-semibold text-purple-400 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            Live Synchronized
          </span>
        </div>

        {metrics.applications === 0 ? (
          <Card className="p-10 text-center rounded-[28px]">
            <p className="text-sm font-semibold text-slate-400">
              No applications analyzed yet. Enter a website URL above to start autonomous discovery.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
            <Card className="p-5 text-center rounded-2xl">
              <span className="text-[11px] font-semibold text-slate-400 block mb-1">Applications</span>
              <span className="text-3xl font-black text-white tracking-tight">{metrics.applications}</span>
            </Card>

            <Card className="p-5 text-center rounded-2xl">
              <span className="text-[11px] font-semibold text-slate-400 block mb-1">Generated Tests</span>
              <span className="text-3xl font-black text-purple-300 tracking-tight">{metrics.generated_tests}</span>
            </Card>

            <Card className="p-5 text-center rounded-2xl">
              <span className="text-[11px] font-semibold text-slate-400 block mb-1">Executions</span>
              <span className="text-3xl font-black text-white tracking-tight">{metrics.executions}</span>
            </Card>

            <Card className="p-5 text-center rounded-2xl">
              <span className="text-[11px] font-semibold text-slate-400 block mb-1">QAOA Runs</span>
              <span className="text-3xl font-black text-purple-300 tracking-tight">{metrics.optimizations}</span>
            </Card>

            <Card className="p-5 text-center rounded-2xl">
              <span className="text-[11px] font-semibold text-slate-400 block mb-1">Detected Defects</span>
              <span className={`text-3xl font-black tracking-tight ${metrics.detected_defects > 0 ? 'text-rose-400' : 'text-slate-300'}`}>
                {metrics.detected_defects}
              </span>
            </Card>

            <Card className="p-5 text-center rounded-2xl">
              <span className="text-[11px] font-semibold text-slate-400 block mb-1">Pass Rate</span>
              <span className="text-3xl font-black text-emerald-400 tracking-tight">{metrics.pass_rate}%</span>
            </Card>
          </div>
        )}
      </div>

      {/* Six-Stage Regression Pipeline Architecture */}
      <div className="space-y-4 pt-4">
        <div className="px-2">
          <span className="text-xs font-mono uppercase tracking-widest text-slate-400 font-bold">
            Core Architecture
          </span>
          <h3 className="text-xl font-black text-white tracking-tight mt-1">
            Six-Stage Intelligent Regression Pipeline
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {workflowSteps.map((step) => {
            const Icon = step.icon;
            return (
              <Card
                key={step.num}
                className="p-6 rounded-[24px] space-y-3 hover:border-purple-500/30 transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-purple-300 bg-purple-500/15 px-2.5 py-1 rounded-full border border-purple-500/20">
                    {step.num}
                  </span>
                  <div className="w-9 h-9 rounded-2xl bg-purple-500/15 text-purple-300 flex items-center justify-center border border-purple-500/20">
                    <Icon className="w-4 h-4" />
                  </div>
                </div>

                <div>
                  <h4 className="font-extrabold text-sm text-white tracking-tight">
                    {step.subtitle}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    {step.desc}
                  </p>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Recent Analyzed Target Applications */}
      {recentApps.length > 0 && (
        <div className="space-y-4 pt-4">
          <div className="flex items-center justify-between px-2">
            <h3 className="text-xl font-black text-white tracking-tight">
              Recent Target Applications
            </h3>
            <button
              onClick={() => navigate('/applications')}
              className="text-xs font-bold text-purple-300 hover:text-purple-200 flex items-center gap-1 cursor-pointer"
            >
              <span>View All Applications</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recentApps.map((app) => (
              <Card
                key={app.id}
                className="p-6 rounded-[24px] space-y-4 hover:border-purple-500/30 transition-all"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h4 className="font-bold text-sm text-white truncate">
                      {app.name || app.url}
                    </h4>
                    <p className="text-xs font-mono text-slate-400 truncate mt-0.5">
                      {app.url}
                    </p>
                  </div>
                  <StatusBadge status={app.status} size="sm" />
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-2xl bg-white/5 border border-white/10 text-center">
                    <span className="text-slate-400 block text-[10px]">Pages</span>
                    <strong className="text-white">{app.discovered_pages || 0}</strong>
                  </div>
                  <div className="p-2.5 rounded-2xl bg-white/5 border border-white/10 text-center">
                    <span className="text-slate-400 block text-[10px]">Elements</span>
                    <strong className="text-purple-300">{app.discovered_elements || 0}</strong>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={() => navigate(`/test-cases?app_id=${app.id}`)}
                    disabled={app.status === 'failed' || app.status === 'error' || app.status === 'analyzing'}
                    className="flex-1 h-9 rounded-full btn-burgundy text-white text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer transition-colors shadow-xs disabled:opacity-40 disabled:cursor-not-allowed"
                    title={app.status === 'failed' || app.status === 'error' ? 'Complete website discovery and generate valid tests first.' : 'View Tests'}
                  >
                    <FileCheck className="w-3.5 h-3.5" />
                    <span>View Tests</span>
                  </button>
                  <button
                    onClick={() => navigate(`/optimization?app_id=${app.id}`)}
                    disabled={app.status === 'failed' || app.status === 'error' || app.status === 'analyzing'}
                    className="h-9 px-4 rounded-full btn-pill-outline text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    title={app.status === 'failed' || app.status === 'error' ? 'Complete website discovery and generate valid tests first.' : 'QAOA'}
                  >
                    <Atom className="w-3.5 h-3.5 text-purple-400" />
                    <span>QAOA</span>
                  </button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default OverviewPage;
