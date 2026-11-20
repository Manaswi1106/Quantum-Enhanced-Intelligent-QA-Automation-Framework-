const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

async function request<T>(path: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  const timeoutMs = options?.timeoutMs ?? 60000 // default 60s timeout
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(url, {
      ...options,
      signal: options?.signal || controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(error.detail || `Request failed: ${res.status}`)
    }

    return res.json()
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`)
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

export const api = {
  // Applications
  analyzeUrl: (url: string, force: boolean = false) =>
    request<any>('/applications/analyze', {
      method: 'POST',
      body: JSON.stringify({ url, force }),
    }),
  getApplications: () => request<any[]>('/applications'),
  getApplication: (id: number) => request<any>(`/applications/${id}`),
  deleteApplication: (id: number) =>
    request<any>(`/applications/${id}`, { method: 'DELETE' }),

  // Test Cases
  getTestCases: (appId?: number) =>
    request<any[]>(`/test-cases${appId ? `?app_id=${appId}` : ''}`),
  createTestCase: (data: any) =>
    request<any>('/test-cases', { method: 'POST', body: JSON.stringify(data) }),
  generateTestCases: (appId: number) =>
    request<any>('/test-cases/generate', {
      method: 'POST',
      body: JSON.stringify({ app_id: appId }),
    }),

  // Execution
  executeTests: (data: { app_id: number; test_case_ids?: number[] }) =>
    request<any>('/tests/execute', { method: 'POST', body: JSON.stringify(data) }),
  getExecution: (id: number) => request<any>(`/executions/${id}`),

  // History
  getHistory: (testCaseId?: number) =>
    request<any[]>(`/history${testCaseId ? `?test_case_id=${testCaseId}` : ''}`),

  // Optimization
  buildQubo: (data: { app_id: number; weights?: any; budget?: number }) =>
    request<any>('/optimization/qubo', { method: 'POST', body: JSON.stringify(data) }),
  runQaoa: (data: { app_id: number; weights?: any; budget?: number; p?: number; shots?: number }) =>
    request<any>('/optimization/qaoa', { method: 'POST', body: JSON.stringify(data) }),

  // Results
  getResults: (appId?: number) =>
    request<any>(`/results${appId ? `?app_id=${appId}` : ''}`),

  // Version comparison
  compareVersions: (data: { baseline_url: string; new_url: string }) =>
    request<any>('/versions/compare', { method: 'POST', body: JSON.stringify(data) }),

  // Overview Metrics
  getOverviewMetrics: () => request<any>('/overview/metrics'),

  // AI Provider Status
  getAIStatus: () => request<{ configured: boolean; provider: string | null; message: string }>('/ai/status'),

  // Developer Regression Report
  getDeveloperReport: (appId?: number, executionId?: number) => {
    const params = new URLSearchParams()
    if (appId) params.append('app_id', String(appId))
    if (executionId) params.append('execution_id', String(executionId))
    const qs = params.toString()
    return request<any>(`/reports/developer${qs ? `?${qs}` : ''}`)
  },

  // Version 2 Application Regression
  createApplicationVersion: (data: { baseline_app_id: number; new_url: string; version_label?: string }) =>
    request<any>('/applications/version', { method: 'POST', body: JSON.stringify(data) }),

  // Database Reset
  resetDatabase: () =>
    request<any>('/reset', { method: 'POST' }),
}
