import React, { useState, useEffect } from 'react'
import Header from './components/Header'
import Navigation from './components/Navigation'
import UploadForm from './components/UploadForm'
import ResultsDashboard from './components/ResultsDashboard'
import ReferenceDataPage from './components/ReferenceDataPage'
import LoadingScreen from './components/LoadingScreen'
import Footer from './components/Footer'

class ErrorBoundary extends React.Component {
    constructor(props) { super(props); this.state = { hasError: false, error: null } }
    static getDerivedStateFromError(error) { return { hasError: true, error } }
    render() {
        if (this.state.hasError) return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', padding: 40, background: 'var(--bg)' }}>
                <div className="glass-card" style={{ padding: '50px 40px', maxWidth: 500, textAlign: 'center' }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: 16 }}>🛑</div>
                    <h3 style={{ fontSize: '1.2rem', letterSpacing: '-0.03em', marginBottom: 12 }}>System Error</h3>
                    <p className="mono" style={{ color: 'var(--red)', marginBottom: 20 }}>{this.state.error?.message}</p>
                    <button className="laser-btn" onClick={() => window.location.reload()}>Reload</button>
                </div>
            </div>
        )
        return this.props.children
    }
}

export default function App() {
    const [view, setView] = useState('upload')
    const [resultsData, setResultsData] = useState(null)
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)
    const [progressLogs, setProgressLogs] = useState([])

    const handleAnalyze = async (formData) => {
        setLoading(true)
        setError(null)
        setProgressLogs([])
        setResultsData(null)

        try {
            const resp = await fetch('/api/analyze', { method: 'POST', body: formData })
            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}))
                throw new Error(errData.detail || `Server error ${resp.status}`)
            }

            const reader = resp.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ''
            let finalResult = null

            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop()

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue
                    const payload = line.slice(6).trim()
                    if (!payload) continue
                    try {
                        const msg = JSON.parse(payload)
                        if (msg.type === 'progress') {
                            setProgressLogs(prev => [...prev, { step: msg.step, message: msg.message, ts: Date.now() }])
                        } else if (msg.type === 'result') {
                            finalResult = msg.data
                        } else if (msg.type === 'error') {
                            throw new Error(msg.message)
                        }
                    } catch (parseErr) {
                        if (parseErr.message && !parseErr.message.includes('JSON')) throw parseErr
                    }
                }
            }

            if (finalResult) {
                setResultsData(finalResult)
                setView('results')
            }
        } catch (err) {
            console.error('Analyze request error:', err)
            setError(err.message || 'Analysis failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <ErrorBoundary>
            <div style={{ minHeight: '100vh', position: 'relative', overflow: 'hidden' }}>
                {/* Refraction glows */}
                <div className="glow-blob" style={{ width: 500, height: 500, top: '-10%', right: '-5%' }} />
                <div className="glow-blob" style={{ width: 400, height: 400, bottom: '10%', left: '-8%', opacity: 0.08 }} />

                <div style={{ maxWidth: 1600, margin: '0 auto', padding: '0 32px', position: 'relative', zIndex: 1 }}>
                    <Header />
                    <Navigation activeView={view} onNavigate={setView} hasResults={!!resultsData} />

                    <main style={{ paddingBottom: 80, minHeight: '65vh' }}>
                        {/* Upload view */}
                        {view === 'upload' && !loading && (
                            <div className="animate-slide-up">
                                <UploadForm onSubmit={handleAnalyze} />
                                {error && (
                                    <div className="glass-card" style={{ marginTop: 20, padding: '16px 24px', borderColor: 'rgba(255, 68, 68, 0.3)' }}>
                                        <p className="mono" style={{ color: 'var(--red)' }}>🔴 {error}</p>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Loading — full-screen overlay */}
                        {loading && <LoadingScreen progressLogs={progressLogs} />}

                        {/* Results */}
                        {view === 'results' && resultsData && !loading && (
                            <ResultsDashboard data={resultsData} onNewAnalysis={() => { setView('upload'); setResultsData(null); setError(null) }} />
                        )}

                        {/* Reference Data */}
                        {view === 'reference' && !loading && <ReferenceDataPage />}
                    </main>

                    <Footer />
                </div>
            </div>
        </ErrorBoundary>
    )
}
