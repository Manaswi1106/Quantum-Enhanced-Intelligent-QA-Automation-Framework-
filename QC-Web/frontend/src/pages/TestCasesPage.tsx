import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Search,
  FileCheck,
  ChevronDown,
  ChevronUp,
  Atom,
  AlertCircle,
  Key,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { StatusBadge } from '../components/ui/StatusBadge';
import { api } from '../services/api';
import type { TestCase } from '../types';

export default function TestCasesPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [aiStatus, setAiStatus] = useState<{ configured: boolean; provider: string | null; message: string }>({
    configured: false,
    provider: null,
    message: '',
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('All');
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  // Load apps and check query param
  useEffect(() => {
    const loadAppsAndStatus = async () => {
      try {
        const [apps, status] = await Promise.all([
          api.getApplications().catch(() => []),
          api.getAIStatus().catch(() => ({ configured: false, provider: null, message: '' })),
        ]);

        setApplications(apps || []);
        setAiStatus(status);

        const qAppId = searchParams.get('app_id');
        if (qAppId && apps.some((a: any) => a.id === Number(qAppId))) {
          setSelectedAppId(Number(qAppId));
        } else if (apps && apps.length > 0) {
          setSelectedAppId(apps[0].id);
        } else {
          setSelectedAppId(null);
          setLoading(false);
        }
      } catch (e) {
        console.error('Failed to load initial data:', e);
        setLoading(false);
      }
    };
    loadAppsAndStatus();
  }, [searchParams]);

  const fetchTestCases = async (appId: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getTestCases(appId);
      setTestCases(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch test cases from Supabase.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedAppId) {
      fetchTestCases(selectedAppId);
    }
  }, [selectedAppId]);

  const handleGenerate = async () => {
    if (!selectedAppId) return;
    try {
      setGenerating(true);
      setError(null);
      await api.generateTestCases(selectedAppId);
      await fetchTestCases(selectedAppId);
    } catch (err: any) {
      setError(err.message || 'Failed to generate test cases.');
    } finally {
      setGenerating(false);
    }
  };

  const toggleRow = (id: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectedApp = applications.find((a) => a.id === selectedAppId);

  // Filter test cases dynamically
  const filteredTests = testCases.filter((tc) => {
    const matchesSearch =
      tc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tc.test_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tc.description && tc.description.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesPriority =
      priorityFilter === 'All' || tc.priority.toLowerCase() === priorityFilter.toLowerCase();

    return matchesSearch && matchesPriority;
  });

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            <span className="text-xs font-mono uppercase tracking-widest text-purple-300 font-bold">
              Dynamic AI Repository {aiStatus.configured && `• ${aiStatus.provider?.toUpperCase()}`}
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Regression Test Repository
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Candidate regression tests synthesized from observed application structure and user workflows.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Target App Selector */}
          {applications.length > 0 && (
            <div className="rounded-full bg-[#0F172A] border border-white/10 p-1 shadow-2xs">
              <select
                value={selectedAppId || ''}
                onChange={(e) => setSelectedAppId(Number(e.target.value))}
                className="bg-transparent text-white text-xs font-bold px-3 py-1.5 rounded-full focus:outline-none cursor-pointer"
              >
                {applications.map((app) => (
                  <option key={app.id} value={app.id} className="bg-[#0F172A] text-white">
                    {app.name || app.url} (App #{app.id})
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating || !selectedAppId}
            className="h-11 px-5 rounded-full btn-burgundy text-white text-xs font-bold tracking-wide uppercase shadow-lg flex items-center gap-2 cursor-pointer transition-all disabled:opacity-60 shrink-0"
          >
            {generating ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Synthesizing AI Tests...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-purple-200" />
                <span>Generate AI Tests</span>
              </>
            )}
          </button>

          {testCases.length > 0 && (
            <button
              onClick={() => navigate(`/optimization?app_id=${selectedAppId}`)}
              className="h-11 px-5 rounded-full btn-pill-outline text-white text-xs font-bold tracking-wide shadow-xs flex items-center gap-2 cursor-pointer transition-all shrink-0"
            >
              <Atom className="w-4 h-4 text-purple-400" />
              <span>Optimize with QAOA</span>
            </button>
          )}
        </div>
      </div>

      {/* Target Application Header Card */}
      {selectedApp && (
        <Card className="p-6 rounded-[24px]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-purple-400 shadow-[0_0_8px_#A855F7]" />
              <div className="min-w-0 max-w-full">
                <span className="text-xs text-slate-400 font-semibold block">Target Application:</span>
                <div className="flex items-center gap-2 flex-wrap min-w-0">
                  <h3 className="font-extrabold text-base text-white truncate max-w-xs sm:max-w-md">
                    {selectedApp.name || selectedApp.url}
                  </h3>
                  <span
                    className="font-mono text-xs text-purple-300 truncate max-w-xs sm:max-w-sm block break-all"
                    title={selectedApp.url}
                  >
                    ({selectedApp.url})
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="text-slate-400">
                Discovered Pages: <strong className="text-white">{selectedApp.discovered_pages || 0}</strong>
              </span>
              <span className="text-slate-400">
                Candidate Tests: <strong className="text-purple-300">{testCases.length}</strong>
              </span>
            </div>
          </div>
        </Card>
      )}

      {/* AI Not Configured Notice */}
      {!aiStatus.configured && (
        <Card className="p-5 bg-amber-950/30 border border-amber-500/30 text-amber-200 text-xs font-medium rounded-2xl flex items-center gap-3 shadow-xs">
          <Key className="w-5 h-5 text-amber-400 shrink-0" />
          <div className="flex-1">
            <strong className="block text-amber-300">AI provider not configured.</strong>
            <span>Add <code className="bg-black/30 px-1.5 py-0.5 rounded text-amber-200">GEMINI_API_KEY</code> or <code className="bg-black/30 px-1.5 py-0.5 rounded text-amber-200">OPENAI_API_KEY</code> in <code className="bg-black/30 px-1.5 py-0.5 rounded text-amber-200">backend/.env</code> to enable real AI test generation for any crawled website.</span>
          </div>
        </Card>
      )}

      {error && (
        <Card className="p-5 bg-rose-950/30 border border-rose-500/30 text-rose-200 text-xs font-medium rounded-2xl flex items-center gap-3 shadow-xs">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </Card>
      )}

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search tests by title or TC-ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-11 pl-11 pr-4 bg-[#0F172A] border border-white/10 rounded-full text-xs font-medium text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/40 shadow-2xs"
          />
        </div>

        {/* Priority Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 rounded-full bg-[#0F172A] border border-white/10 text-xs font-medium self-start sm:self-auto">
          {['All', 'Critical', 'High', 'Medium', 'Low'].map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPriorityFilter(p)}
              className={`px-3.5 py-1 rounded-full transition-all cursor-pointer ${
                priorityFilter.toLowerCase() === p.toLowerCase()
                  ? 'bg-purple-600 text-white font-bold shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Test Cases List */}
      {loading ? (
        <LoadingState message="Retrieving candidate test repository from Supabase..." />
      ) : applications.length === 0 ? (
        <Card className="p-12 text-center rounded-[28px]">
          <EmptyState
            icon={FileCheck}
            title="No application analyzed yet"
            description="Go to Overview or Applications to ingest a target website URL first."
          />
        </Card>
      ) : testCases.length === 0 ? (
        <Card className="p-12 text-center rounded-[28px]">
          <EmptyState
            icon={FileCheck}
            title="No test cases generated yet"
            description={
              aiStatus.configured
                ? "Click 'Generate AI Tests' above to synthesize dynamic regression tests for this website."
                : "Add GEMINI_API_KEY or OPENAI_API_KEY in backend/.env to synthesize dynamic tests for this website."
            }
          />
          {aiStatus.configured && (
            <div className="mt-6 flex justify-center">
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="h-11 px-6 rounded-full btn-burgundy text-white text-xs font-bold uppercase tracking-wider shadow-lg flex items-center gap-2 cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-purple-200" />
                <span>Generate AI Tests Now</span>
              </button>
            </div>
          )}
        </Card>
      ) : filteredTests.length === 0 ? (
        <Card className="p-12 text-center rounded-[28px]">
          <EmptyState
            icon={Search}
            title="No matching test cases found"
            description="Try adjusting your search query or priority filters."
          />
        </Card>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
              Candidate Test Cases ({filteredTests.length})
            </span>
            <span className="text-xs font-mono text-purple-400 font-semibold">
              Ready for QUBO/QAOA Selection
            </span>
          </div>

          <div className="space-y-3">
            {filteredTests.map((tc) => {
              const isExpanded = expandedRows.has(tc.id);

              return (
                <Card
                  key={tc.id}
                  className="p-5 rounded-2xl transition-all hover:border-purple-500/30"
                >
                  <div
                    onClick={() => toggleRow(tc.id)}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none"
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="mt-0.5 px-2 py-0.5 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 font-mono text-xs font-bold shrink-0">
                        {tc.test_id}
                      </div>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-extrabold text-sm text-white truncate">
                            {tc.name}
                          </h4>
                          {tc.source && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/5 text-slate-400">
                              {tc.source}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 mt-1 line-clamp-1">
                          {tc.description}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                      <StatusBadge status={tc.priority} size="sm" />
                      <span className="text-xs font-mono text-slate-400">
                        Cost: {tc.execution_cost}s
                      </span>
                      <div className="w-6 h-6 rounded-full bg-white/5 flex items-center justify-center text-slate-400">
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Step Details */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-white/10 space-y-4">
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-center">
                          <span className="text-slate-400 block text-[10px]">Risk Factor</span>
                          <strong className="text-purple-300 font-bold">{tc.risk}</strong>
                        </div>
                        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-center">
                          <span className="text-slate-400 block text-[10px]">Coverage</span>
                          <strong className="text-white font-bold">{tc.coverage}</strong>
                        </div>
                        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-center">
                          <span className="text-slate-400 block text-[10px]">Impact</span>
                          <strong className="text-purple-300 font-bold">{tc.change_impact}</strong>
                        </div>
                        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-center">
                          <span className="text-slate-400 block text-[10px]">Redundancy</span>
                          <strong className="text-slate-300">{tc.redundancy_group || 'None'}</strong>
                        </div>
                      </div>

                      {tc.steps && tc.steps.length > 0 && (
                        <div>
                          <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-2">
                            Step Execution Sequence:
                          </span>
                          <ol className="space-y-1.5 pl-4 list-decimal text-xs text-slate-300 font-mono">
                            {tc.steps.map((st, i) => (
                              <li key={i}>{st}</li>
                            ))}
                          </ol>
                        </div>
                      )}

                      {tc.expected_result && (
                        <div className="p-3 rounded-xl bg-purple-950/20 border border-purple-500/20 text-xs">
                          <span className="font-bold text-purple-300 block mb-0.5">Expected Assertion:</span>
                          <span className="text-slate-300">{tc.expected_result}</span>
                        </div>
                      )}
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
