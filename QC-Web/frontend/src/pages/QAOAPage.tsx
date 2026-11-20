import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Atom,
  Sliders,
  Layers,
  Play,
  AlertCircle,
  Cpu,
  CheckCircle2,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { api } from '../services/api';

interface Weights {
  change_impact: number;
  failure_rate: number;
  coverage: number;
  risk: number;
  efficiency: number;
}

export default function QAOAPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [applications, setApplications] = useState<any[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [candidateTests, setCandidateTests] = useState<any[]>([]);

  const [weights, setWeights] = useState<Weights>({
    change_impact: 0.30,
    failure_rate: 0.20,
    coverage: 0.20,
    risk: 0.20,
    efficiency: 0.10,
  });

  const [budget, setBudget] = useState(5);
  const [p, setP] = useState(1);
  const [shots, setShots] = useState(512);

  const [optimizationResult, setOptimizationResult] = useState<any | null>(null);
  const [quboMatrix, setQuboMatrix] = useState<number[][] | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load applications
  useEffect(() => {
    const loadApps = async () => {
      try {
        const apps = await api.getApplications();
        if (apps && apps.length > 0) {
          setApplications(apps);
          const qAppId = searchParams.get('app_id');
          if (qAppId && apps.some((a: any) => a.id === Number(qAppId))) {
            setSelectedAppId(Number(qAppId));
          } else {
            setSelectedAppId(apps[0].id);
          }
        }
      } catch (err) {
        console.error('Failed to load apps:', err);
      }
    };
    loadApps();
  }, [searchParams]);

  // Load candidate tests for selected application
  useEffect(() => {
    if (!selectedAppId) return;

    const loadCandidates = async () => {
      try {
        setError(null);
        const tests = await api.getTestCases(selectedAppId);
        setCandidateTests(tests || []);
        if (tests && tests.length > 0) {
          setBudget(Math.min(5, tests.length));
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load candidate tests.');
      }
    };
    loadCandidates();
  }, [selectedAppId]);

  const selectedApp = applications.find((a) => a.id === selectedAppId);

  const handleWeightSlider = (key: keyof Weights, val: number) => {
    setWeights((prev) => ({
      ...prev,
      [key]: val,
    }));
  };

  const handleOptimize = async () => {
    if (!selectedAppId || candidateTests.length === 0) return;

    setIsRunning(true);
    setError(null);

    try {
      // 1. Build QUBO
      const quboData = await api.buildQubo({
        app_id: selectedAppId,
        budget,
        weights,
      });
      if (quboData.qubo_matrix) {
        setQuboMatrix(quboData.qubo_matrix);
      }

      // 2. Run QAOA simulation via Qiskit Aer
      const result = await api.runQaoa({
        app_id: selectedAppId,
        budget,
        p,
        shots,
        weights,
      });

      setOptimizationResult(result);
      if (result.qubo_matrix) {
        setQuboMatrix(result.qubo_matrix);
      }
    } catch (err: any) {
      setError(err.message || 'QAOA simulation failed.');
    } finally {
      setIsRunning(false);
    }
  };

  const handleExecuteSelected = () => {
    if (!selectedAppId) return;
    navigate(`/execution?app_id=${selectedAppId}&mode=qaoa`);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            <span className="text-xs font-mono uppercase tracking-widest text-purple-300 font-bold">
              Combinatorial Optimization
            </span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            QAOA Quantum Test Optimization
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Combinatorial test selection formulated as a QUBO and simulated via Qiskit Aer quantum circuits.
          </p>
        </div>

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
      </div>

      {applications.length === 0 ? (
        <Card className="p-12 text-center rounded-[28px]">
          <EmptyState
            icon={Atom}
            title="No applications analyzed yet"
            description="Analyze a target website first to synthesize candidate tests before optimizing."
          />
        </Card>
      ) : candidateTests.length === 0 ? (
        <Card className="p-12 text-center rounded-[28px]">
          <EmptyState
            icon={Layers}
            title="No candidate tests generated yet"
            description="Generate AI tests on the Test Cases page for this application before running QAOA."
            action={
              <button
                onClick={() => navigate(`/test-cases?app_id=${selectedAppId}`)}
                className="h-11 px-6 rounded-full btn-burgundy text-white text-xs font-bold uppercase shadow-md cursor-pointer"
              >
                Go to Test Cases Repository
              </button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Target App Card */}
          {selectedApp && (
            <Card className="p-6 rounded-[24px]">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-purple-400 shadow-[0_0_8px_#A855F7]" />
                  <div className="min-w-0 max-w-full">
                    <span className="text-xs text-slate-400 font-semibold block">Active Optimization Target:</span>
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
                  <div className="p-2.5 rounded-2xl bg-white/5 border border-white/10 text-center">
                    <span className="text-slate-400 block text-[10px]">Candidate Tests</span>
                    <strong className="text-purple-300 text-base">{candidateTests.length}</strong>
                  </div>
                  <div className="p-2.5 rounded-2xl bg-white/5 border border-white/10 text-center">
                    <span className="text-slate-400 block text-[10px]">Selection Budget</span>
                    <strong className="text-white text-base">{budget}</strong>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Configuration Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Weights & Budget (5 cols) */}
            <div className="lg:col-span-5 space-y-6">
              <Card className="p-6 sm:p-7 rounded-[28px] space-y-5">
                <div className="flex items-center justify-between pb-3 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-purple-400" />
                    <h3 className="font-bold text-sm text-white">QUBO Objective Weights</h3>
                  </div>
                  <span className="text-[10px] font-mono text-purple-300 uppercase font-bold">Configurable</span>
                </div>

                <div className="space-y-4 text-xs">
                  <div>
                    <div className="flex justify-between mb-1.5 font-mono font-bold">
                      <span className="text-slate-300">Change Impact</span>
                      <strong className="text-purple-300">{(weights.change_impact * 100).toFixed(0)}%</strong>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={weights.change_impact}
                      onChange={(e) => handleWeightSlider('change_impact', parseFloat(e.target.value))}
                      disabled={isRunning}
                      className="w-full accent-purple-500 cursor-pointer"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1.5 font-mono font-bold">
                      <span className="text-slate-300">Historical Failure Rate</span>
                      <strong className="text-purple-300">{(weights.failure_rate * 100).toFixed(0)}%</strong>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={weights.failure_rate}
                      onChange={(e) => handleWeightSlider('failure_rate', parseFloat(e.target.value))}
                      disabled={isRunning}
                      className="w-full accent-purple-500 cursor-pointer"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1.5 font-mono font-bold">
                      <span className="text-slate-300">Functional Coverage</span>
                      <strong className="text-purple-300">{(weights.coverage * 100).toFixed(0)}%</strong>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={weights.coverage}
                      onChange={(e) => handleWeightSlider('coverage', parseFloat(e.target.value))}
                      disabled={isRunning}
                      className="w-full accent-purple-500 cursor-pointer"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1.5 font-mono font-bold">
                      <span className="text-slate-300">Business Risk</span>
                      <strong className="text-purple-300">{(weights.risk * 100).toFixed(0)}%</strong>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={weights.risk}
                      onChange={(e) => handleWeightSlider('risk', parseFloat(e.target.value))}
                      disabled={isRunning}
                      className="w-full accent-purple-500 cursor-pointer"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between mb-1.5 font-mono font-bold">
                      <span className="text-slate-300">Execution Efficiency</span>
                      <strong className="text-purple-300">{(weights.efficiency * 100).toFixed(0)}%</strong>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={weights.efficiency}
                      onChange={(e) => handleWeightSlider('efficiency', parseFloat(e.target.value))}
                      disabled={isRunning}
                      className="w-full accent-purple-500 cursor-pointer"
                    />
                  </div>
                </div>

                <div className="pt-3 border-t border-white/10 space-y-3">
                  <div className="flex items-center justify-between text-xs font-mono font-bold">
                    <span className="text-slate-300">Selection Budget Limit</span>
                    <strong className="text-purple-300">{budget} of {candidateTests.length} tests</strong>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max={Math.max(1, candidateTests.length)}
                    value={budget}
                    onChange={(e) => setBudget(parseInt(e.target.value))}
                    disabled={isRunning}
                    className="w-full accent-purple-500 cursor-pointer"
                  />
                </div>
              </Card>

              {/* Quantum Circuit Parameters Card */}
              <Card className="p-6 rounded-[28px] space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-white/10 text-xs font-mono">
                  <span className="text-white font-bold flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-purple-400" />
                    <span>Qiskit Aer Parameters</span>
                  </span>
                  <span className="text-purple-300 font-bold">Simulation</span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                  <div className="p-3 rounded-2xl bg-white/5 border border-white/10">
                    <span className="text-slate-400 block text-[10px] mb-1">Circuit Layers (p)</span>
                    <select
                      value={p}
                      onChange={(e) => setP(Number(e.target.value))}
                      disabled={isRunning}
                      className="w-full bg-[#0F172A] border border-white/15 rounded-xl text-white font-bold p-1.5 text-xs"
                    >
                      <option value={1}>1 layer (COBYLA)</option>
                      <option value={2}>2 layers (COBYLA)</option>
                    </select>
                  </div>
                  <div className="p-3 rounded-2xl bg-white/5 border border-white/10">
                    <span className="text-slate-400 block text-[10px] mb-1">Sampling Shots</span>
                    <select
                      value={shots}
                      onChange={(e) => setShots(Number(e.target.value))}
                      disabled={isRunning}
                      className="w-full bg-[#0F172A] border border-white/15 rounded-xl text-purple-300 font-bold p-1.5 text-xs"
                    >
                      <option value={256}>256 shots</option>
                      <option value={512}>512 shots</option>
                      <option value={1024}>1024 shots</option>
                    </select>
                  </div>
                </div>

                {quboMatrix && (
                  <div className="p-3 rounded-2xl bg-purple-950/20 border border-purple-500/20 text-[11px] font-mono text-purple-300 flex items-center justify-between font-bold">
                    <span>QUBO Formulation:</span>
                    <span>{quboMatrix.length}×{quboMatrix.length} terms</span>
                  </div>
                )}

                <button
                  onClick={handleOptimize}
                  disabled={isRunning || candidateTests.length === 0}
                  className="w-full h-12 rounded-full btn-burgundy text-white font-bold text-xs uppercase tracking-wider shadow-lg flex items-center justify-center gap-2 cursor-pointer transition-all disabled:opacity-60"
                >
                  {isRunning ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Simulating QAOA Circuit...</span>
                    </>
                  ) : (
                    <>
                      <Atom className="w-4 h-4 text-purple-200" />
                      <span>Run QAOA Optimization</span>
                    </>
                  )}
                </button>
              </Card>
            </div>

            {/* Right: Quantum Simulation Result & Test Selection (7 cols) */}
            <div className="lg:col-span-7 space-y-6">
              {error && (
                <div className="p-4 rounded-2xl bg-rose-950/30 border border-rose-500/30 text-rose-200 text-xs flex items-center gap-2 font-medium">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {optimizationResult ? (
                <div className="space-y-5">
                  <div className="card-velvet p-7 sm:p-8 rounded-[32px] space-y-5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-11 h-11 rounded-2xl bg-white/10 border border-white/20 flex items-center justify-center text-white">
                          <Atom className="w-6 h-6 animate-spin [animation-duration:10s]" />
                        </div>
                        <div>
                          <h3 className="text-xl font-black text-white tracking-tight">
                            QAOA Simulation — Qiskit Aer
                          </h3>
                          <span className="text-xs font-mono text-purple-200">
                            State Evolution: 512 shots • COBYLA Convergence
                          </span>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="text-[10px] uppercase font-mono text-slate-400 block">Objective Energy</span>
                        <strong className="text-2xl font-black font-mono text-white">
                          {(optimizationResult.objective_value || 0).toFixed(4)}
                        </strong>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono pt-1">
                      <div className="p-3 rounded-2xl bg-white/5 border border-white/10 text-center">
                        <span className="text-slate-400 block text-[10px]">Candidate Tests</span>
                        <strong className="text-white text-base">{candidateTests.length}</strong>
                      </div>
                      <div className="p-3 rounded-2xl bg-white/5 border border-white/10 text-center">
                        <span className="text-slate-400 block text-[10px]">QAOA Selected</span>
                        <strong className="text-purple-300 text-base">
                          {optimizationResult.selected_tests?.length || 0}
                        </strong>
                      </div>
                      <div className="p-3 rounded-2xl bg-white/5 border border-white/10 text-center">
                        <span className="text-slate-400 block text-[10px]">Excluded Tests</span>
                        <strong className="text-slate-300 text-base">
                          {optimizationResult.excluded_tests?.length || 0}
                        </strong>
                      </div>
                      <div className="p-3 rounded-2xl bg-white/5 border border-white/10 text-center">
                        <span className="text-slate-400 block text-[10px]">Optimization Budget</span>
                        <strong className="text-white text-base">{budget}</strong>
                      </div>
                    </div>

                    <div className="pt-2">
                      <button
                        onClick={handleExecuteSelected}
                        className="w-full h-12 rounded-full bg-white hover:bg-slate-100 text-purple-950 font-bold text-xs uppercase tracking-wider shadow-lg flex items-center justify-center gap-2 cursor-pointer transition-all"
                      >
                        <Play className="w-4 h-4 fill-purple-950" />
                        <span>Execute QAOA-Selected Tests with Playwright ({optimizationResult.selected_tests?.length || 0})</span>
                      </button>
                    </div>
                  </div>

                  {/* Selected Tests List */}
                  <div className="space-y-3">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 px-1">
                      QAOA Selected Regression Tests ({optimizationResult.selected_tests?.length || 0})
                    </span>

                    <div className="space-y-2.5">
                      {candidateTests
                        .filter((t) => optimizationResult.selected_tests?.includes(t.id))
                        .map((t) => (
                          <Card
                            key={t.id}
                            className="p-4 sm:p-5 rounded-2xl flex items-center justify-between gap-4"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <span className="font-mono text-xs font-bold text-purple-300 bg-purple-500/15 px-2 py-0.5 rounded-lg border border-purple-500/20 shrink-0">
                                {t.test_id}
                              </span>
                              <div className="min-w-0">
                                <h4 className="font-bold text-xs text-white truncate">
                                  {t.name}
                                </h4>
                                <span className="text-[11px] font-mono text-slate-400">
                                  Risk: {((t.risk || 0.5) * 100).toFixed(0)}% • Impact: {((t.change_impact || 0.5) * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>

                            <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/30 px-2.5 py-1 rounded-full border border-emerald-500/30 shrink-0 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              <span>Selected</span>
                            </span>
                          </Card>
                        ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="card-velvet p-12 text-center rounded-[32px] flex flex-col items-center justify-center min-h-[380px]">
                  <div className="w-20 h-20 rounded-3xl bg-white/10 border border-white/20 flex items-center justify-center text-white mb-5 shadow-inner">
                    <Atom className="w-10 h-10 animate-spin [animation-duration:14s]" />
                  </div>
                  <h3 className="text-xl font-bold text-white tracking-tight">
                    Ready for Quantum Optimization
                  </h3>
                  <p className="text-xs text-slate-300 max-w-md mt-2 leading-relaxed">
                    Adjust the objective weights and selection budget limit on the left, then click{' '}
                    <strong className="text-white">Run QAOA Optimization</strong> to formulate the QUBO Hamiltonian and sample the optimal test subset using Qiskit Aer.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
