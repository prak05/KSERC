import { useEffect, useRef, useState } from 'react'

/* Live audit terminal: streams pipeline progress as it is reported by /api/status. */

const STAGES = [
    { id: 'extract', label: 'Extract', match: ['submit', 'upload', 'extract'] },
    { id: 'deep', label: 'Tables', match: ['deep', 'table', 'ocr', 'vision'] },
    { id: 'myt', label: 'MYT norms', match: ['myt', 'norm'] },
    { id: 'anomaly', label: 'Anomaly', match: ['anomal'] },
    { id: 'audit', label: 'Audit', match: ['audit', 'ai_audit', 'depreciation', 'interest', 'rm'] },
    { id: 'review', label: 'Review', match: ['review'] },
    { id: 'draft', label: 'Draft', match: ['draft', 'order'] },
    { id: 'clarify', label: 'Clarify', match: ['clarif'] },
    { id: 'validate', label: 'Validate', match: ['valid', 'complete', 'done'] },
]

const stageIndex = (step = '') => {
    const s = String(step).toLowerCase()
    const i = STAGES.findIndex(st => st.match.some(m => s.includes(m)))
    return i < 0 ? 0 : i
}

const clock = (ms) => {
    const s = Math.floor(ms / 1000)
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

export default function LoadingScreen({ progressLogs = [] }) {
    const [start] = useState(() => Date.now())
    const [now, setNow] = useState(() => Date.now())
    const logRef = useRef(null)

    useEffect(() => {
        const t = setInterval(() => setNow(Date.now()), 1000)
        return () => clearInterval(t)
    }, [])

    useEffect(() => {
        logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
    }, [progressLogs.length])

    const live = progressLogs.reduce((m, l) => Math.max(m, stageIndex(l.step)), 0)
    const pct = Math.round(((live + 0.5) / STAGES.length) * 100)
    const lines = progressLogs.length ? progressLogs : [{ step: 'submit', message: 'Preparing analysis', ts: start }]

    return (
        <section className="stack view" aria-live="polite">
            <header className="page-head enter-frame">
                <div>
                    <span className="label">Audit in progress</span>
                    <h1 className="h1 enter-title">Reading the petition.</h1>
                    <p className="lede" style={{ marginTop: 8 }}>
                        Large petitions take several minutes. You can leave this page open; results appear the moment the pipeline finishes.
                    </p>
                </div>
                <div className="row">
                    <span className="label">Elapsed</span>
                    <span className="num" style={{ fontSize: 22 }}>{clock(now - start)}</span>
                </div>
            </header>

            <div className="terminal enter-panel">
                <div className="terminal-head">
                    <span className="label">Pipeline log</span>
                    <span className="spacer" />
                    <span className="mono faint" style={{ fontSize: 11 }}>{STAGES[live].label} · {pct}%</span>
                </div>
                <div className="progress"><span style={{ width: `${pct}%` }} /></div>
                <div className="log" ref={logRef}>
                    {lines.map((l, i) => (
                        <div className="log-line" key={`${i}-${l.message}`}>
                            <span className="t">{clock((l.ts || start) - start)}</span>
                            <span className="s">{STAGES[stageIndex(l.step)].label}</span>
                            <span className="m">{l.message}</span>
                        </div>
                    ))}
                </div>
                <div className="stage-list">
                    {STAGES.map((s, i) => (
                        <div key={s.id} className={`stage ${i < live ? 'is-done' : ''} ${i === live ? 'is-live' : ''}`}>
                            <span className="faint">{String(i + 1).padStart(2, '0')}</span> {s.label}
                        </div>
                    ))}
                </div>
            </div>
        </section>
    )
}
