import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { OverviewPage } from './pages/OverviewPage'
import { ApplicationsPage } from './pages/ApplicationsPage'
import TestCasesPage from './pages/TestCasesPage'
import ExecutionPage from './pages/ExecutionPage'
import QAOAPage from './pages/QAOAPage'
import HistoryPage from './pages/HistoryPage'
import ResultsPage from './pages/ResultsPage'

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/applications" element={<ApplicationsPage />} />
            <Route path="/test-cases" element={<TestCasesPage />} />
            <Route path="/execution" element={<ExecutionPage />} />
            <Route path="/optimization" element={<QAOAPage />} />
            <Route path="/qaoa" element={<QAOAPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/results" element={<ResultsPage />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  )
}
