import { useEffect, useState } from 'react'
import { Notice, PageHead, StatusPill } from './ui'

export default function CaseHistory({ onOpen }) {
    const [cases, setCases] = useState(null)
    const [error, setError] = useState(null)
    const [opening, setOpening] = useState(null)
    const [filter, setFilter] = useState('all')

    useEffect(() => {
        fetch('/api/analyses')
            .then(r => (r.ok ? r.json() : Promise.reject(new Error(`Case history unavailable (${r.status})`))))
            .then(d => setCases(d.analyses || []))
            .catch(e => { setError(e.message); setCases([]) })
    }, [])

    const open = async (c) => {
        if (c.status !== 'COMPLETED') return
        setOpening(c.analysis_id)
        try {
            const r = await fetch(`/api/status/${c.analysis_id}`)
            const d = await r.json()
            if (!r.ok || !d.result) throw new Error('This analysis has no stored result')
            onOpen(d.result)
        } catch (e) {
            setError(e.message)
        } finally {
            setOpening(null)
        }
    }

    const licensees = [...new Set((cases || []).map(c => c.licensee).filter(Boolean))]
    const shown = (cases || []).filter(c => filter === 'all' || c.licensee === filter)

    return (
        <section className="stack view">
            <PageHead eyebrow="Cases" title="Case history" lede="Every analysis run on this deployment. Open a completed case to review, edit or draft its order.">
                {licensees.length > 1 && (
                    <div className="segmented">
                        <button className={filter === 'all' ? 'is-active' : ''} onClick={() => setFilter('all')}>All</button>
                        {licensees.map(l => <button key={l} className={filter === l ? 'is-active' : ''} onClick={() => setFilter(l)}>{l}</button>)}
                    </div>
                )}
            </PageHead>

            {error && <Notice tone="bad" onClose={() => setError(null)}>{error}</Notice>}

            <div className="card enter-panel">
                {cases === null && <div className="progress is-indeterminate"><span /></div>}
                {cases !== null && shown.length === 0 ? (
                    <div className="empty"><p className="h3">No cases yet</p><p>Run an analysis from Upload &amp; analyse; it will be listed here.</p></div>
                ) : (
                    <div className="table-wrap">
                        <table className="table">
                            <thead><tr><th>Licensee</th><th>Financial year</th><th>Status</th><th>Updated</th><th>Analysis</th><th /></tr></thead>
                            <tbody>
                                {shown.map(c => (
                                    <tr key={c.analysis_id} className={c.status === 'COMPLETED' ? 'is-clickable' : ''} onClick={() => open(c)}>
                                        <td style={{ fontWeight: 500 }}>{c.licensee || '—'}</td>
                                        <td className="num">{c.financial_year ? `FY ${c.financial_year}` : '—'}</td>
                                        <td><StatusPill status={c.status} /></td>
                                        <td className="num faint">{c.updated_at ? new Date(c.updated_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'}</td>
                                        <td className="num faint">{c.analysis_id?.slice(0, 8)}</td>
                                        <td className="r">{c.status === 'COMPLETED' && <span className="btn btn-sm">{opening === c.analysis_id ? 'Opening…' : 'Open'}</span>}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </section>
    )
}
