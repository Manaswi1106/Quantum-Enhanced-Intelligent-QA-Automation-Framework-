export interface Application {
  id: number
  name: string
  url: string
  status: 'analyzing' | 'active' | 'error'
  discovered_pages: number
  discovered_elements: number
  created_at: string
}

export interface ApplicationVersion {
  id: number
  app_id: number
  version_label: string
  url: string
  analysis_data: AnalysisData | null
  created_at: string
}

export interface AnalysisData {
  title: string
  reachable: boolean
  pages: DiscoveredPage[]
  forms: DiscoveredForm[]
  links: string[]
  buttons: string[]
  inputs: string[]
  interactive_elements: number
}

export interface DiscoveredPage {
  url: string
  title: string
  path: string
}

export interface DiscoveredForm {
  action: string
  method: string
  fields: string[]
  page: string
}

export interface TestCase {
  id: number
  test_id: string
  name: string
  description: string
  steps: string[]
  expected_result: string
  source: 'manual' | 'automatic'
  priority: 'critical' | 'high' | 'medium' | 'low'
  risk: number
  coverage: number
  change_impact: number
  execution_cost: number
  redundancy_group: string | null
  historical_runs: number
  historical_failures: number
  failure_rate: number
  status: 'not_run' | 'passed' | 'failed' | 'selected' | 'excluded'
  app_id: number
  original_test_id?: string | null
  app_version_id?: number | null
  created_at: string
  updated_at: string
}

export interface TestExecution {
  id: number
  app_version_id: number
  started_at: string
  completed_at: string | null
  total: number
  passed: number
  failed: number
  skipped: number
  status: 'running' | 'completed' | 'error'
}

export interface TestResult {
  id: number
  execution_id: number
  test_case_id: number
  test_id: string
  test_name: string
  status: 'passed' | 'failed' | 'skipped' | 'error'
  failure_category?: string | null
  duration_ms: number
  error_message: string | null
  screenshot_path: string | null
  created_at: string
}

export interface OptimizationRun {
  id: number
  execution_id: number | null
  qubo_size: number
  qaoa_params: QAOAParams
  selected_tests: number[]
  excluded_tests: number[]
  objective_value: number
  created_at: string
}

export interface QAOAParams {
  p: number
  shots: number
  optimizer: string
  weights: OptimizationWeights
  budget: number
}

export interface OptimizationWeights {
  change_impact: number
  failure_rate: number
  coverage: number
  risk: number
  efficiency: number
}

export interface TestHistory {
  id: number
  test_case_id: number
  test_id: string
  execution_id: number
  status: 'passed' | 'failed' | 'skipped' | 'error'
  failure_category?: string | null
  duration_ms: number
  failure_reason: string | null
  timestamp: string
}

export interface ReleaseReadiness {
  status: 'ready' | 'changes_required' | 'not_evaluated'
  total_tests: number
  passed: number
  failed: number
  skipped: number
  blocking_failures: TestResult[]
  recommendations: string[]
  evaluated_at: string | null
}

export interface VersionComparison {
  baseline_version: string
  new_version: string
  new_pages: string[]
  removed_pages: string[]
  changed_elements: string[]
  affected_tests: number[]
}
