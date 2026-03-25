import React, { useState, useEffect } from 'react'
import Header from './components/Header'
import Navigation from './components/Navigation'
import UploadForm from './components/UploadForm'
import ResultsDashboard from './components/ResultsDashboard'
import ReferenceDataPage from './components/ReferenceDataPage'
import RegulationManager from './components/RegulationManager'
import LoadingScreen from './components/LoadingScreen'
import OrderDrafter from './components/OrderDrafter'
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


/* ── R&M Review Modal ─────────────────────────────────────────── */
function RMReviewModal({ rmData, analysisId, onContinue, onCancel }) {
    const items = rmData?.rm_line_items || []
    const rmNorm = rmData?.rm_norm || 0
    const claimedRm = rmData?.claimed_rm || 0

    // Initialize: items classified as ONE_TIME_RM are pre-selected
    const [selected, setSelected] = useState(() => {
        const s = {}
        items.forEach((item, i) => {
            s[i] = item.classification === 'ONE_TIME_RM'
        })
        return s
    })
    const [submitting, setSubmitting] = useState(false)

    const selectedItems = items.filter((_, i) => selected[i])
    const oneTimeTotal = selectedItems.reduce((sum, it) => sum + (it.amount || 0), 0)
    const approvedRm = rmNorm + oneTimeTotal

    const classColors = {
        'CAPITAL_EXPENDITURE': { bg: 'rgba(255, 168, 0, 0.15)', border: 'rgba(255, 168, 0, 0.4)', label: '⚠️ Capital', color: '#ffa800' },
        'ONE_TIME_RM': { bg: 'rgba(0, 255, 136, 0.12)', border: 'rgba(0, 255, 136, 0.4)', label: '✅ One-Time', color: '#00ff88' },
        'ROUTINE_RM': { bg: 'rgba(255, 68, 68, 0.12)', border: 'rgba(255, 68, 68, 0.4)', label: '🔴 Routine', color: '#ff4444' },
    }

    const handleContinue = async () => {
        setSubmitting(true)
        try {
            const resp = await fetch('/api/rm-continue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    analysis_id: analysisId,
                    selected_items: selectedItems,
                }),
            })
            if (!resp.ok) throw new Error('Failed to continue')
            onContinue()
        } catch (e) {
            console.error('R&M continue failed:', e)
            setSubmitting(false)
        }
    }

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 24,
        }}>
            <div className="glass-card" style={{
                maxWidth: 800, width: '100%', maxHeight: '90vh', overflow: 'auto',
                padding: '32px 36px', border: '1px solid rgba(0, 255, 136, 0.3)',
            }}>
                {/* Header */}
                <div style={{ marginBottom: 24 }}>
                    <h2 style={{ fontSize: '1.4rem', letterSpacing: '-0.03em', marginBottom: 8, color: 'var(--green)' }}>
                        ⚡ R&M One-Time Expenditure Review
                    </h2>
                    <p className="mono" style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)', lineHeight: 1.6 }}>
                        The licensee claimed <strong style={{ color: '#fff' }}>Rs. {claimedRm.toFixed(2)}L</strong> for R&M,
                        which exceeds the MYT norm of <strong style={{ color: '#fff' }}>Rs. {rmNorm.toFixed(2)}L</strong>.
                        <br />Select which items should be allowed as <strong style={{ color: 'var(--green)' }}>one-time expenditure</strong> under Regulation 80(3).
                    </p>
                </div>

                {/* Items list */}
                <div style={{ marginBottom: 24 }}>
                    {items.map((item, i) => {
                        const cls = classColors[item.classification] || classColors['ROUTINE_RM']
                        return (
                            <div key={i}
                                onClick={() => setSelected(s => ({ ...s, [i]: !s[i] }))}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 12,
                                    padding: '12px 16px', marginBottom: 8, borderRadius: 8,
                                    background: selected[i] ? 'rgba(0, 255, 136, 0.08)' : 'rgba(255,255,255,0.03)',
                                    border: `1px solid ${selected[i] ? 'rgba(0, 255, 136, 0.3)' : 'rgba(255,255,255,0.08)'}`,
                                    cursor: 'pointer', transition: 'all 0.2s ease',
                                }}>
                                {/* Checkbox */}
                                <div style={{
                                    width: 20, height: 20, borderRadius: 4, flexShrink: 0,
                                    border: `2px solid ${selected[i] ? 'var(--green)' : 'rgba(255,255,255,0.3)'}`,
                                    background: selected[i] ? 'var(--green)' : 'transparent',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    transition: 'all 0.2s ease',
                                }}>
                                    {selected[i] && <span style={{ color: '#000', fontSize: 12, fontWeight: 700 }}>✓</span>}
                                </div>

                                {/* Description + Classification */}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: '0.9rem', color: '#fff', marginBottom: 4 }}>
                                        {item.description}
                                    </div>
                                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                                        <span className="mono" style={{
                                            fontSize: '0.7rem', padding: '2px 8px', borderRadius: 4,
                                            background: cls.bg, border: `1px solid ${cls.border}`, color: cls.color,
                                        }}>
                                            {cls.label}
                                        </span>
                                        {item.reason && (
                                            <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>
                                                {item.reason}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {/* Amount */}
                                <div className="mono" style={{
                                    fontSize: '0.9rem', fontWeight: 600,
                                    color: selected[i] ? 'var(--green)' : 'rgba(255,255,255,0.5)',
                                    flexShrink: 0,
                                }}>
                                    ₹{item.amount?.toFixed(2)}L
                                </div>
                            </div>
                        )
                    })}
                </div>

                {/* Summary bar */}
                <div style={{
                    display: 'flex', gap: 24, padding: '16px 20px', borderRadius: 8,
                    background: 'rgba(0, 255, 136, 0.05)', border: '1px solid rgba(0, 255, 136, 0.2)',
                    marginBottom: 24, flexWrap: 'wrap',
                }}>
                    <div>
                        <div className="mono" style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>MYT Norm</div>
                        <div className="mono" style={{ fontSize: '1rem', color: '#fff' }}>₹{rmNorm.toFixed(2)}L</div>
                    </div>
                    <div style={{ color: 'var(--green)', fontSize: '1.5rem', alignSelf: 'center' }}>+</div>
                    <div>
                        <div className="mono" style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>One-Time ({selectedItems.length} items)</div>
                        <div className="mono" style={{ fontSize: '1rem', color: 'var(--green)' }}>₹{oneTimeTotal.toFixed(2)}L</div>
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: '1.5rem', alignSelf: 'center' }}>=</div>
                    <div>
                        <div className="mono" style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginBottom: 2 }}>Approved R&M</div>
                        <div className="mono" style={{ fontSize: '1.1rem', color: '#fff', fontWeight: 700 }}>₹{approvedRm.toFixed(2)}L</div>
                    </div>
                </div>

                {/* Buttons */}
                <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                    <button
                        onClick={handleContinue}
                        disabled={submitting}
                        className="laser-btn"
                        style={{ padding: '10px 28px', fontSize: '0.9rem' }}
                    >
                        {submitting ? '⏳ Continuing…' : `✅ Continue Analysis (${selectedItems.length} items selected)`}
                    </button>
                </div>
            </div>
        </div>
    )
}


export default function App() {
    const [view, setView] = useState('upload')
    const [resultsData, setResultsData] = useState(null)
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)
    const [progressLogs, setProgressLogs] = useState([])
    
    // R&M review pause state
    const [rmReview, setRmReview] = useState(null)  // { analysisId, rmData }

    const handleAnalyze = async (formData) => {
        setLoading(true)
        setError(null)
        setProgressLogs([])
        setResultsData(null)
        setRmReview(null)

        try {
            // Step 1: Submit the analysis
            const resp = await fetch('/api/analyze', { method: 'POST', body: formData })
            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}))
                throw new Error(errData.detail || `Server error ${resp.status}`)
            }

            const { analysis_id } = await resp.json()
            console.log('[KSERC] New analysis started:', analysis_id)
            setProgressLogs(prev => [...prev, { step: 'submit', message: 'Analysis submitted, processing…', ts: Date.now() }])

            // Step 2: Poll for completion (handles PENDING_RM_REVIEW pause)
            await pollForCompletion(analysis_id)
        } catch (err) {
            console.error('Analyze request error:', err)
            setError(err.message || 'Analysis failed')
        } finally {
            setLoading(false)
        }
    }

    const pollForCompletion = async (analysisId) => {
        let attempts = 0
        const maxAttempts = 240  // 20 minutes max (5s intervals)
        while (attempts < maxAttempts) {
            await new Promise(r => setTimeout(r, 5000))  // 5 second intervals
            attempts++

            try {
                const statusResp = await fetch(`/api/status/${analysisId}`)
                if (!statusResp.ok) continue
                const statusData = await statusResp.json()

                // Add progress logs if available
                if (statusData.progress && statusData.progress.length > 0) {
                    setProgressLogs(prev => {
                        const existing = new Set(prev.map(p => p.message))
                        const newLogs = statusData.progress
                            .filter(p => p.msg && !existing.has(p.msg))
                            .map(p => ({ step: p.stage, message: p.msg, ts: Date.now() }))
                        return [...prev, ...newLogs]
                    })
                }

                console.log(`[KSERC] Poll #${attempts}: status=${statusData.status}, progress=${statusData.progress?.length || 0} entries`)

                if (statusData.status === 'COMPLETED') {
                    console.log('[KSERC] Analysis completed, showing results')
                    setResultsData(statusData.result)
                    setView('results')
                    return
                } else if (statusData.status === 'FAILED') {
                    throw new Error(statusData.result?.error || 'Analysis failed')
                } else if (statusData.status === 'PENDING_RM_REVIEW') {
                    console.log('[KSERC] Pipeline paused for R&M review')
                    setProgressLogs(prev => [...prev, {
                        step: 'rm_review',
                        message: '⚡ R&M items extracted — waiting for your review…',
                        ts: Date.now(),
                    }])
                    // Show R&M review modal
                    setRmReview({ analysisId, rmData: statusData.result })
                    setLoading(false)
                    return  // Stop polling — will resume after user selects items
                }
            } catch (pollErr) {
                if (pollErr.message && !pollErr.message.includes('fetch')) throw pollErr
                // Network error during poll — retry
            }
        }

        if (attempts >= maxAttempts) {
            throw new Error('Analysis timed out after 20 minutes')
        }
    }

    const handleRMContinue = async () => {
        // User has submitted R&M selections, resume polling
        const analysisId = rmReview.analysisId
        setRmReview(null)
        setLoading(true)
        setProgressLogs(prev => [...prev, {
            step: 'rm_review',
            message: '✅ R&M selections applied. Resuming analysis…',
            ts: Date.now(),
        }])

        try {
            await pollForCompletion(analysisId)
        } catch (err) {
            console.error('Resume polling error:', err)
            setError(err.message || 'Analysis resume failed')
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
                        {view === 'upload' && !loading && !rmReview && (
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

                        {/* R&M Review Modal — shown when pipeline pauses */}
                        {rmReview && (
                            <RMReviewModal
                                rmData={rmReview.rmData}
                                analysisId={rmReview.analysisId}
                                onContinue={handleRMContinue}
                                onCancel={() => setRmReview(null)}
                            />
                        )}

                        {/* Results */}
                        {view === 'results' && resultsData && !loading && (
                            <ResultsDashboard
                                data={resultsData}
                                onNewAnalysis={() => { setView('upload'); setResultsData(null); setError(null) }}
                                onDraftOrder={() => setView('drafter')}
                            />
                        )}

                        {/* Order Drafter */}
                        {view === 'drafter' && resultsData && !loading && (
                            <OrderDrafter
                                analysisId={resultsData.analysis_id}
                                analysisData={resultsData}
                                onBack={() => setView('results')}
                            />
                        )}

                        {/* Reference Data */}
                        {view === 'reference' && !loading && <ReferenceDataPage />}

                        {/* Regulations */}
                        {view === 'regulations' && !loading && <RegulationManager />}
                    </main>

                    <Footer />
                </div>
            </div>
        </ErrorBoundary>
    )
}
