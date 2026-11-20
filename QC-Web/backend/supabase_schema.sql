-- =============================================================================
-- QC-Web: Supabase PostgreSQL Schema Migration
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Applications table
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(1024) NOT NULL,
    status VARCHAR(50) DEFAULT 'analyzing',
    discovered_pages INTEGER DEFAULT 0,
    discovered_elements INTEGER DEFAULT 0,
    analysis_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Discovered Pages table
CREATE TABLE IF NOT EXISTS discovered_pages (
    id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    url VARCHAR(2048) NOT NULL,
    path VARCHAR(1024) NOT NULL,
    title VARCHAR(512),
    status_code INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_discovered_pages_app_id ON discovered_pages(app_id);

-- 3. Interactive Elements table
CREATE TABLE IF NOT EXISTS interactive_elements (
    id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    page_id INTEGER REFERENCES discovered_pages(id) ON DELETE CASCADE,
    element_type VARCHAR(50) NOT NULL,
    tag_name VARCHAR(50),
    selector VARCHAR(1024),
    testid VARCHAR(255),
    name VARCHAR(255),
    text TEXT,
    page_path VARCHAR(1024),
    attributes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_interactive_elements_app_id ON interactive_elements(app_id);
CREATE INDEX IF NOT EXISTS idx_interactive_elements_page_id ON interactive_elements(page_id);

-- 4. Application Versions table
CREATE TABLE IF NOT EXISTS application_versions (
    id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    version_label VARCHAR(50) NOT NULL,
    url VARCHAR(1024) NOT NULL,
    analysis_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_application_versions_app_id ON application_versions(app_id);

-- 5. Test Cases table
CREATE TABLE IF NOT EXISTS test_cases (
    id SERIAL PRIMARY KEY,
    test_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    steps JSONB DEFAULT '[]'::jsonb,
    expected_result TEXT,
    source VARCHAR(50) DEFAULT 'manual',
    priority VARCHAR(50) DEFAULT 'medium',
    risk DOUBLE PRECISION DEFAULT 0.5,
    coverage DOUBLE PRECISION DEFAULT 0.5,
    change_impact DOUBLE PRECISION DEFAULT 0.5,
    execution_cost DOUBLE PRECISION DEFAULT 1.0,
    redundancy_group VARCHAR(100),
    status VARCHAR(50) DEFAULT 'not_run',
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_test_cases_app_id ON test_cases(app_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_test_id ON test_cases(test_id);

-- 6. Executions table
CREATE TABLE IF NOT EXISTS executions (
    id SERIAL PRIMARY KEY,
    app_version_id INTEGER REFERENCES application_versions(id) ON DELETE SET NULL,
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total INTEGER DEFAULT 0,
    passed INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    skipped INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'running'
);
CREATE INDEX IF NOT EXISTS idx_executions_app_id ON executions(app_id);

-- 7. Execution Results table
CREATE TABLE IF NOT EXISTS execution_results (
    id SERIAL PRIMARY KEY,
    execution_id INTEGER NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    test_case_id INTEGER NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'skipped',
    duration_ms INTEGER DEFAULT 0,
    error_message TEXT,
    screenshot_path VARCHAR(1024),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_execution_results_execution_id ON execution_results(execution_id);
CREATE INDEX IF NOT EXISTS idx_execution_results_test_case_id ON execution_results(test_case_id);

-- 8. Optimization Results (QUBO / QAOA runs) table
CREATE TABLE IF NOT EXISTS optimization_results (
    id SERIAL PRIMARY KEY,
    app_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    execution_id INTEGER REFERENCES executions(id) ON DELETE SET NULL,
    qubo_matrix JSONB,
    qubo_size INTEGER DEFAULT 0,
    qaoa_params JSONB,
    selected_tests JSONB DEFAULT '[]'::jsonb,
    excluded_tests JSONB DEFAULT '[]'::jsonb,
    objective_value DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_optimization_results_app_id ON optimization_results(app_id);

-- 9. History table
CREATE TABLE IF NOT EXISTS history (
    id SERIAL PRIMARY KEY,
    test_case_id INTEGER NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    execution_id INTEGER NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    duration_ms INTEGER DEFAULT 0,
    failure_reason TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_history_test_case_id ON history(test_case_id);
CREATE INDEX IF NOT EXISTS idx_history_execution_id ON history(execution_id);

-- =============================================================================
-- Row Level Security (RLS) & Policies
-- =============================================================================

ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovered_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactive_elements ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE optimization_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE history ENABLE ROW LEVEL SECURITY;

-- Development policy: allow full access for service and authenticated roles
DO $$
BEGIN
    EXECUTE 'CREATE POLICY "Allow public full access applications" ON applications FOR ALL USING (true) WITH CHECK (true)';
    EXECUTE 'CREATE POLICY "Allow public full access discovered_pages" ON discovered_pages FOR ALL USING (true) WITH CHECK (true)';
    EXECUTE 'CREATE POLICY "Allow public full access interactive_elements" ON interactive_elements FOR ALL USING (true) WITH CHECK (true)';
    EXECUTE 'CREATE POLICY "Allow public full access application_versions" ON application_versions FOR ALL USING (true) WITH CHECK (true)';
    EXECUTE 'CREATE POLICY "Allow public full access test_cases" ON test_cases FOR ALL USING (true) WITH CHECK (true)';
    EXECUTE 'CREATE POLICY "Allow public full access executions" ON executions FOR ALL USING (true) WITH CHECK (true)';
    EXECUTE 'CREATE POLICY "Allow public full access execution_results" ON execution_results FOR ALL USING (true) WITH CHECK (true)';
    EXECUTE 'CREATE POLICY "Allow public full access optimization_results" ON optimization_results FOR ALL USING (true) WITH CHECK (true)';
    EXECUTE 'CREATE POLICY "Allow public full access history" ON history FOR ALL USING (true) WITH CHECK (true)';
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
