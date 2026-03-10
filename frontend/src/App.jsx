import React, { useState } from 'react'
import Header from './components/Header'
import GovBar from './components/GovBar'
import Navigation from './components/Navigation'
import UploadForm from './components/UploadForm'
import LoadingScreen from './components/LoadingScreen'
import ResultsDashboard from './components/ResultsDashboard'
import ReferenceDataPage from './components/ReferenceDataPage'
import Footer from './components/Footer'
import TubesBackground from './components/TubesBackground'

const LICENSEES = ['Technopark', 'Infopark', 'CSEZA', 'KDHP']
const FINANCIAL_YEARS = ['2024-25', '2023-24', '2022-23', '2021-22', '2020-21', '2019-20', '2018-19']

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMsg: '', stack: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, errorMsg: error.message };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ stack: errorInfo.componentStack });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 bg-red-50 border-2 border-red-500 rounded-xl my-8">
          <h2 className="text-2xl font-bold text-red-700 mb-4">UI Rendering Crash Detected</h2>
          <p className="text-red-900 font-mono mb-2"><strong>Error:</strong> {this.state.errorMsg}</p>
          <pre className="text-xs text-red-800 bg-red-100 p-4 rounded overflow-x-auto">
            {this.state.stack}
          </pre>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded font-bold"
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const [currentView, setCurrentView] = useState('upload') // upload | loading | results | reference
  const [analysisResult, setAnalysisResult] = useState(null)
  const [error, setError] = useState(null)
  const [progressLog, setProgressLog] = useState([])

  const STAGE_ICONS = { extract: '📄', audit: '🔢', ai_audit: '🤖', draft: '📝' }

  const handleAnalyze = async (formData) => {
    setCurrentView('loading')
    setError(null)

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Analysis start failed' }))
        throw new Error(err.detail || `Server error: ${res.status}`)
      }

      const initData = await res.json()
      const analysisId = initData.analysis_id

      // Setup polling
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(`/api/status/${analysisId}`)
          if (!statusRes.ok) throw new Error('Failed to fetch status')

          const statusData = await statusRes.json()

          // Update live progress log
          if (statusData.progress && statusData.progress.length > 0) {
            setProgressLog(statusData.progress)
          }

          if (statusData.status === 'COMPLETED') {
            clearInterval(pollInterval)
            setAnalysisResult(statusData.result)
            setCurrentView('results')
          } else if (statusData.status === 'FAILED') {
            clearInterval(pollInterval)
            setError(statusData.result?.error || 'Analysis failed during processing.')
            setCurrentView('upload')
          }
        } catch (pollingErr) {
          console.error("Polling error:", pollingErr)
          // Optionally we could show a warning, but we keep trying in case of temporary disconnect
        }
      }, 3000)

    } catch (err) {
      console.error("Analyze request error:", err)
      setError(err.message)
      setCurrentView('upload')
    }
  }

  const handleNewAnalysis = () => {
    setAnalysisResult(null)
    setCurrentView('upload')
    setError(null)
  }

  return (
    <TubesBackground>
      <div className="min-h-screen flex flex-col pointer-events-none text-kserc-navy w-full relative z-20">
        <div className="pointer-events-auto w-full">
          <GovBar />
          <Header />
          <Navigation
            currentView={currentView}
            onNavigate={setCurrentView}
            hasResults={!!analysisResult}
          />
        </div>

        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 pointer-events-auto">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-kserc-red animate-fade-in-up">
              <p className="font-semibold">⚠️ Error</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}

          {currentView === 'upload' && (
            <UploadForm
              licensees={LICENSEES}
              financialYears={FINANCIAL_YEARS}
              onSubmit={handleAnalyze}
            />
          )}

          {currentView === 'loading' && (
            <div className="flex flex-col items-center justify-start py-10 animate-fade-in-up">
              <div className="w-full max-w-2xl bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                {/* Header */}
                <div className="bg-kserc-navy text-white px-6 py-4 flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-green-400 animate-pulse" />
                  <span className="font-semibold text-lg">Pipeline Running</span>
                  <span className="ml-auto text-sm text-blue-200 font-mono">
                    {progressLog.length} step{progressLog.length !== 1 ? 's' : ''} logged
                  </span>
                </div>

                {/* Progress feed */}
                <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
                  {progressLog.length === 0 ? (
                    <div className="px-6 py-8 text-center text-gray-400">
                      <div className="text-3xl mb-2">⏳</div>
                      <p className="text-sm">Starting pipeline…</p>
                    </div>
                  ) : (
                    progressLog.map((entry, i) => (
                      <div key={i} className="px-6 py-3 flex items-start gap-3 hover:bg-gray-50">
                        <span className="text-lg mt-0.5 shrink-0">
                          {STAGE_ICONS[entry.stage] || '🔄'}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-800 leading-snug">{entry.msg}</p>
                        </div>
                        <span className="text-xs text-gray-400 font-mono shrink-0 mt-0.5">
                          {entry.ts}
                        </span>
                      </div>
                    ))
                  )}
                  {/* Live pulse at end */}
                  <div className="px-6 py-3 flex items-center gap-2 text-sm text-gray-400">
                    <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse inline-block" />
                    Processing…
                  </div>
                </div>
              </div>
            </div>
          )}

          {currentView === 'results' && analysisResult && (
            <ErrorBoundary>
              <ResultsDashboard
                data={analysisResult}
                onNewAnalysis={handleNewAnalysis}
              />
            </ErrorBoundary>
          )}

          {currentView === 'reference' && (
            <ErrorBoundary>
              <ReferenceDataPage />
            </ErrorBoundary>
          )}
        </main>

        <div className="pointer-events-auto w-full mt-auto">
          <Footer />
        </div>
      </div>
    </TubesBackground>
  )
}

