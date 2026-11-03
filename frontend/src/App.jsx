import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Calculator, Database, FileText, History, Landmark, LayoutList, LogOut, MessageSquare, Scale, Search, Upload } from 'lucide-react'
import Analyst from './components/Analyst'
import Benchmarks from './components/Benchmarks'
import CaseHistory from './components/CaseHistory'
import LoadingScreen from './components/LoadingScreen'
import OrderDrafter from './components/OrderDrafter'
import QuickCalculator from './components/QuickCalculator'
import ReferenceDataPage from './components/ReferenceDataPage'
import RegulationManager from './components/RegulationManager'
import ResultsDashboard from './components/ResultsDashboard'
import UploadForm from './components/UploadForm'
import { Check, Cta, Notice } from './components/ui'
import { fmt } from './components/format'

class ErrorBoundary extends React.Component {
    constructor(props) { super(props); this.state = { error: null } }
    static getDerivedStateFromError(error) { return { error } }
    render() {
        if (!this.state.error) return this.props.children
        return (
            <div className="page"><div className="card empty">
                <p className="h3">Something went wrong</p>
                <p className="mono bad" style={{ margin: '8px 0 18px' }}>{this.state.error.message}</p>
                <button className="btn" onClick={() => window.location.reload()}>Reload</button>
            </div></div>
        )
    }
}

/* ── R&M one-time expenditure review (pipeline pauses on PENDING_RM_REVIEW) ── */
const CLASS = {
    CAPITAL_EXPENDITURE: ['pill-warn', 'Capital'],
    ONE_TIME_RM: ['pill-ok', 'One-time'],
    ROUTINE_RM: ['pill-bad', 'Routine'],
}

function RMReviewModal({ rmData, analysisId, onContinue }) {
    const items = rmData?.rm_line_items || []
    const rmNorm = rmData?.rm_norm || 0
    const claimedRm = rmData?.claimed_rm || 0
    const [selected, setSelected] = useState(() => Object.fromEntries(items.map((it, i) => [i, it.classification === 'ONE_TIME_RM'])))
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    const selectedItems = items.filter((_, i) => selected[i])
    const oneTimeTotal = selectedItems.reduce((sum, it) => sum + (it.amount || 0), 0)

    const handleContinue = async () => {
        setSubmitting(true); setError(null)
        try {
            const resp = await fetch('/api/rm-continue', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ analysis_id: analysisId, selected_items: selectedItems }),
            })
            if (!resp.ok) throw new Error('Could not resume the analysis')
            onContinue()
        } catch (e) {
            setError(e.message); setSubmitting(false)
        }
    }

    return (
        <div className="overlay" role="dialog" aria-modal="true" aria-labelledby="rm-title">
            <div className="modal">
                <div className="card-body" style={{ padding: '22px 24px 16px' }}>
                    <span className="label">Review required · Regulation 80(3)</span>
                    <h2 id="rm-title" className="h1" style={{ fontSize: 22, margin: '8px 0 6px' }}>R&amp;M one-time expenditure</h2>
                    <p className="muted">
                        The licensee claimed <span className="num" style={{ color: 'var(--text)' }}>₹{fmt(claimedRm)} L</span> for R&amp;M against an MYT norm of{' '}
                        <span className="num" style={{ color: 'var(--text)' }}>₹{fmt(rmNorm)} L</span>. Select the items to allow as one-time expenditure.
                    </p>
                </div>
                <div className="divide" style={{ borderTop: '1px solid var(--line)', borderBottom: '1px solid var(--line)' }}>
                    {items.map((item, i) => {
                        const [cls, label] = CLASS[item.classification] || CLASS.ROUTINE_RM
                        return (
                            <div key={i} className="select-row" onClick={() => setSelected(s => ({ ...s, [i]: !s[i] }))}>
                                <Check on={selected[i]} />
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div>{item.description}</div>
                                    <div className="row" style={{ marginTop: 4 }}>
                                        <span className={`pill ${cls}`}>{label}</span>
                                        {item.reason && <span className="faint" style={{ fontSize: 12 }}>{item.reason}</span>}
                                    </div>
                                </div>
                                <span className={`num ${selected[i] ? '' : 'faint'}`}>₹{fmt(item.amount)} L</span>
                            </div>
                        )
                    })}
                </div>
                <div className="metrics" style={{ margin: 16, gridTemplateColumns: 'repeat(3, minmax(0,1fr))' }}>
                    <div className="metric"><span className="label">MYT norm</span><span className="num">{fmt(rmNorm)}</span></div>
                    <div className="metric"><span className="label">One-time · {selectedItems.length} item{selectedItems.length === 1 ? "" : "s"}</span><span className="num">{fmt(oneTimeTotal)}</span></div>
                    <div className="metric"><span className="label">Approved R&amp;M</span><span className="num" style={{ fontWeight: 600 }}>{fmt(rmNorm + oneTimeTotal)}</span></div>
                </div>
                <div className="row" style={{ padding: '0 16px 16px' }}>
                    {error && <span className="bad" style={{ fontSize: 12 }}>{error}</span>}
                    <span className="spacer" />
                    <Cta onClick={handleContinue} disabled={submitting}>{submitting ? 'Resuming…' : `Continue with ${selectedItems.length} item${selectedItems.length === 1 ? '' : 's'}`}</Cta>
                </div>
            </div>
        </div>
    )
}

/* ── Navigation ─────────────────────────────────────────────────────── */
const NAV = [
    { group: 'Workspace', items: [
        { id: 'upload', label: 'Upload & analyse', icon: Upload, key: 'U' },
        { id: 'results', label: 'Analysis results', icon: LayoutList, needsResult: true },
        { id: 'drafter', label: 'Order drafter', icon: FileText, needsResult: true },
        { id: 'history', label: 'Case history', icon: History, key: 'H' },
    ] },
    { group: 'Intelligence', items: [
        { id: 'analyst', label: 'Analyst', icon: MessageSquare, key: 'A' },
        { id: 'calculator', label: 'Quick calculator', icon: Calculator, key: 'C' },
    ] },
    { group: 'Reference', items: [
        { id: 'regulations', label: 'Regulatory corpus', icon: Scale },
        { id: 'reference', label: 'Reference data', icon: Database },
        { id: 'benchmarks', label: 'Precedent & rules', icon: Landmark },
    ] },
]
const ALL_NAV = NAV.flatMap(g => g.items)

function viewFromHash() {
    const id = window.location.hash.replace(/^#\/?/, '')
    return ALL_NAV.some(n => n.id === id) ? id : 'upload'
}

function CommandPalette({ onClose, onSelect, hasResult }) {
    const [q, setQ] = useState('')
    const [active, setActive] = useState(0)
    const inputRef = useRef(null)
    const items = useMemo(() => ALL_NAV
        .filter(i => !i.needsResult || hasResult)
        .filter(i => i.label.toLowerCase().includes(q.toLowerCase())), [q, hasResult])

    useEffect(() => { inputRef.current?.focus() }, [])

    const onKey = (e) => {
        if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(a + 1, items.length - 1)) }
        if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(a - 1, 0)) }
        if (e.key === 'Enter' && items[active]) onSelect(items[active].id)
        if (e.key === 'Escape') onClose()
    }

    return (
        <div className="overlay" onMouseDown={onClose}>
            <div className="palette" onMouseDown={e => e.stopPropagation()} role="dialog" aria-label="Command palette">
                <input ref={inputRef} value={q} placeholder="Go to…" onChange={e => { setQ(e.target.value); setActive(0) }} onKeyDown={onKey} />
                <div className="palette-list">
                    <div className="palette-section label">Navigate</div>
                    {items.map((it, i) => {
                        const Icon = it.icon
                        return (
                            <button key={it.id} className={`palette-item ${i === active ? 'is-active' : ''}`} onMouseEnter={() => setActive(i)} onClick={() => onSelect(it.id)}>
                                <Icon strokeWidth={1.6} />{it.label}{it.key && <span className="kbd">G {it.key}</span>}
                            </button>
                        )
                    })}
                    {items.length === 0 && <div className="empty" style={{ padding: 24 }}>No matches</div>}
                </div>
            </div>
        </div>
    )
}

function Login({ onLogin }) {
    return (
        <div className="login">
            <section className="login-art enter-frame">
                <div className="brand" style={{ padding: 0 }}>
                    <span className="brand-mark">KS</span>
                    <span><span className="brand-name">KSERC</span><br /><span className="brand-sub">Kerala State Electricity Regulatory Commission</span></span>
                </div>
                <h1 className="display login-title enter-title">Truing-up,<br /><em>reviewed.</em></h1>
                <div className="login-meta enter-panel">
                    <div><b>AI truing-up analytical tool</b>FY 2024-25</div>
                    <div><b>RIET Thiruvananthapuram</b>Work order KSERC/CSO/03-05</div>
                </div>
            </section>
            <section className="login-panel">
                <form className="login-form enter-panel" onSubmit={e => { e.preventDefault(); onLogin() }}>
                    <span className="label">Staff sign-in</span>
                    <h2 className="h1" style={{ fontSize: 22, marginBottom: 6 }}>Welcome back</h2>
                    <label className="field"><span className="label">Username</span><input className="input" type="text" placeholder="staff@kserc.gov.in" autoComplete="username" /></label>
                    <label className="field"><span className="label">Password</span><input className="input" type="password" placeholder="••••••••" autoComplete="current-password" /></label>
                    <Cta type="submit" block>Sign in to the portal</Cta>
                    <p className="hint">Authorised access only. Activity is recorded in the audit trail.</p>
                </form>
            </section>
        </div>
    )
}

export default function App() {
    const [loggedIn, setLoggedInState] = useState(() => sessionStorage.getItem('kserc.session') === '1')
    const [view, setViewState] = useState(() => viewFromHash())
    const [resultsData, setResultsData] = useState(null)
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)
    const [progressLogs, setProgressLogs] = useState([])
    const [rmReview, setRmReview] = useState(null)
    const [paletteOpen, setPaletteOpen] = useState(false)

    const setLoggedIn = (on) => {
        if (on) sessionStorage.setItem('kserc.session', '1'); else sessionStorage.removeItem('kserc.session')
        setLoggedInState(on)
    }
    const setView = useCallback((id) => {
        setViewState(id)
        if (viewFromHash() !== id) window.history.pushState(null, '', `#/${id}`)
    }, [])

    useEffect(() => {
        const onHash = () => setViewState(viewFromHash())
        window.addEventListener('popstate', onHash)
        return () => window.removeEventListener('popstate', onHash)
    }, [])

    const go = useCallback((id) => {
        const item = ALL_NAV.find(n => n.id === id)
        if (item?.needsResult && !resultsData) return
        setView(id); setPaletteOpen(false)
    }, [resultsData, setView])

    useEffect(() => {
        let pendingG = false
        const onKey = (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPaletteOpen(o => !o); return }
            const tag = e.target.tagName
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable) return
            if (e.key.toLowerCase() === 'g') { pendingG = true; setTimeout(() => { pendingG = false }, 800); return }
            if (pendingG) {
                const hit = ALL_NAV.find(n => n.key && n.key.toLowerCase() === e.key.toLowerCase())
                if (hit) go(hit.id)
                pendingG = false
            }
        }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [go])

    const pushLog = (step, message) => setProgressLogs(prev => [...prev, { step, message, ts: Date.now() }])

    const pollForCompletion = async (analysisId) => {
        const maxAttempts = 240 // 20 minutes at 5 s
        for (let attempts = 1; attempts <= maxAttempts; attempts++) {
            await new Promise(r => setTimeout(r, 5000))
            try {
                const statusResp = await fetch(`/api/status/${analysisId}`)
                if (!statusResp.ok) continue
                const statusData = await statusResp.json()
                if (statusData.progress?.length) {
                    setProgressLogs(prev => {
                        const seen = new Set(prev.map(p => p.message))
                        const fresh = statusData.progress.filter(p => p.msg && !seen.has(p.msg)).map(p => ({ step: p.stage, message: p.msg, ts: Date.now() }))
                        return [...prev, ...fresh]
                    })
                }
                if (statusData.status === 'COMPLETED') {
                    setResultsData(statusData.result); setView('results'); return
                } else if (statusData.status === 'FAILED') {
                    throw new Error(statusData.result?.error || 'Analysis failed')
                } else if (statusData.status === 'PENDING_RM_REVIEW') {
                    pushLog('review', 'R&M items extracted — waiting for your review')
                    setRmReview({ analysisId, rmData: statusData.result })
                    setLoading(false)
                    return
                }
            } catch (pollErr) {
                if (pollErr.message && !pollErr.message.includes('fetch')) throw pollErr
            }
        }
        throw new Error('Analysis timed out after 20 minutes')
    }

    const handleAnalyze = async (formData) => {
        setLoading(true); setError(null); setProgressLogs([]); setResultsData(null); setRmReview(null)
        try {
            const resp = await fetch('/api/analyze', { method: 'POST', body: formData })
            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}))
                throw new Error(errData.detail || `Server error ${resp.status}`)
            }
            const { analysis_id } = await resp.json()
            pushLog('submit', 'Petition received — analysis queued')
            await pollForCompletion(analysis_id)
        } catch (err) {
            setError(err.message || 'Analysis failed')
        } finally {
            setLoading(false)
        }
    }

    const handleRMContinue = async () => {
        const analysisId = rmReview.analysisId
        setRmReview(null); setLoading(true)
        pushLog('review', 'R&M selections applied — resuming')
        try {
            await pollForCompletion(analysisId)
        } catch (err) {
            setError(err.message || 'Could not resume the analysis')
        } finally {
            setLoading(false)
        }
    }

    if (!loggedIn) return <Login onLogin={() => setLoggedIn(true)} />

    const shownView = ALL_NAV.find(n => n.id === view)?.needsResult && !resultsData ? 'upload' : view
    const current = ALL_NAV.find(n => n.id === shownView)
    const group = NAV.find(g => g.items.includes(current))?.group

    return (
        <ErrorBoundary>
            <div className="shell enter-frame">
                <aside className="sidebar">
                    <div className="brand">
                        <span className="brand-mark">KS</span>
                        <span><span className="brand-name">KSERC</span><br /><span className="brand-sub">Truing-up · FY 2024-25</span></span>
                    </div>
                    {NAV.map(g => (
                        <div key={g.group} className="nav-group">
                            <span className="label">{g.group}</span>
                            {g.items.map(it => {
                                const Icon = it.icon
                                return (
                                    <button key={it.id} className={`nav-item ${shownView === it.id ? 'is-active' : ''}`}
                                        disabled={it.needsResult && !resultsData} onClick={() => go(it.id)}>
                                        <Icon strokeWidth={1.6} />{it.label}
                                        {it.key && <span className="kbd">G {it.key}</span>}
                                    </button>
                                )
                            })}
                        </div>
                    ))}
                    <div className="sidebar-foot">
                        Model · Claude on Amazon Bedrock<br />
                        Work order KSERC/CSO/03-05<br />
                        RIET Thiruvananthapuram
                    </div>
                </aside>

                <div className="main">
                    <header className="topbar">
                        <div className="crumbs"><span>{group}</span><span>/</span><b>{current?.label}</b></div>
                        <div className="topbar-right">
                            <button className="cmd-trigger" onClick={() => setPaletteOpen(true)}>
                                <Search size={13} strokeWidth={1.6} /><span>Search or jump to…</span><span className="kbd">⌘K</span>
                            </button>
                            <span className="avatar" title="staff@kserc.gov.in">KS</span>
                            <button className="btn btn-ghost btn-sm" onClick={() => setLoggedIn(false)} title="Sign out"><LogOut size={13} strokeWidth={1.6} /></button>
                        </div>
                    </header>

                    <main className="page">
                        {shownView === 'upload' && !loading && !rmReview && (
                            <div className="stack view">
                                <UploadForm onSubmit={handleAnalyze} />
                                {error && <Notice tone="bad" onClose={() => setError(null)}>{error}</Notice>}
                            </div>
                        )}
                        {loading && <LoadingScreen progressLogs={progressLogs} />}
                        {rmReview && <RMReviewModal rmData={rmReview.rmData} analysisId={rmReview.analysisId} onContinue={handleRMContinue} />}

                        {view === 'results' && resultsData && !loading && (
                            <ResultsDashboard key={resultsData.analysis_id} data={resultsData}
                                onNewAnalysis={() => { setView('upload'); setResultsData(null); setError(null) }}
                                onDraftOrder={() => setView('drafter')} />
                        )}
                        {view === 'drafter' && resultsData && !loading && (
                            <OrderDrafter analysisId={resultsData.analysis_id} analysisData={resultsData} onBack={() => setView('results')} />
                        )}
                        {shownView === 'history' && !loading && <CaseHistory onOpen={(r) => { setResultsData(r); setView('results') }} />}
                        {shownView === 'analyst' && !loading && <Analyst />}
                        {shownView === 'calculator' && !loading && <QuickCalculator />}
                        {shownView === 'reference' && !loading && <ReferenceDataPage />}
                        {shownView === 'regulations' && !loading && <RegulationManager />}
                        {shownView === 'benchmarks' && !loading && <Benchmarks />}
                    </main>
                </div>
            </div>
            {paletteOpen && <CommandPalette onClose={() => setPaletteOpen(false)} onSelect={go} hasResult={!!resultsData} />}
        </ErrorBoundary>
    )
}
