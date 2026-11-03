import { useState } from 'react'
import CourtHearingEditor from './CourtHearingEditor'
import { Chevron, Notice, PageHead, StatusPill } from './ui'
import { fmt, signed } from './format'

const tone = (v) => (v < 0 ? 'bad' : v > 0 ? 'ok' : 'faint')

function Justification({ component, index, editMode, onValueChange, onJustificationChange }) {
    const [open, setOpen] = useState(false)
    const approved = component._editApproved ?? component.approved
    const text = component._editJustification ?? component.justification

    return (
        <div>
            <button className="disclosure" onClick={() => setOpen(o => !o)} aria-expanded={open}>
                <Chevron open={open} />
                <span className="idx">{String(index + 1).padStart(2, '0')}</span>
                <span style={{ flex: 1, fontWeight: 500 }}>{component.name}</span>
                <span className="num muted">{fmt(component.claimed)}</span>
                <span className="faint">→</span>
                <span className="num" style={{ minWidth: 96, textAlign: 'right' }}>{fmt(approved)}</span>
                <StatusPill status={component.status} />
            </button>
            <div className={`collapse ${open ? 'is-open' : ''}`}>
                <div>
                    <div style={{ padding: '4px 16px 18px 52px' }} className="stack">
                        <div className="metrics">
                            <div className="metric"><span className="label">MYT norm</span><span className="num">{fmt(component.proposed_myt || 0)}</span></div>
                            <div className="metric"><span className="label">Claimed</span><span className="num">{fmt(component.claimed)}</span></div>
                            <div className="metric">
                                <span className="label">Approved</span>
                                {editMode
                                    ? <input type="number" step="any" className="input input-sm num" style={{ marginTop: 4 }} value={approved}
                                        onChange={e => onValueChange(component.key, parseFloat(e.target.value) || 0)} />
                                    : <span className="num">{fmt(approved)}</span>}
                            </div>
                            <div className="metric">
                                <span className="label">Variance</span>
                                <span className={`num ${tone(component.variance)}`}>{signed(component.variance)}
                                    <span className="faint" style={{ fontSize: 11 }}> ({component.variance_pct > 0 ? '+' : ''}{component.variance_pct}%)</span></span>
                            </div>
                        </div>
                        <div>
                            <span className="label" style={{ display: 'block', marginBottom: 8 }}>Commission's observation</span>
                            {editMode
                                ? <textarea className="textarea" rows={4} value={text} onChange={e => onJustificationChange(component.key, e.target.value)} />
                                : <p className="muted" style={{ lineHeight: 1.75, maxWidth: '86ch' }}>{text}</p>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default function ResultsDashboard({ data, onNewAnalysis, onDraftOrder }) {
    const isSurplus = data.final_revenue_gap_surplus >= 0
    const [editMode, setEditMode] = useState(false)
    const [components, setComponents] = useState(data.components || [])
    const [saving, setSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState(null)
    const [auditLog, setAuditLog] = useState([])

    const handleDownload = () => window.open(`/api/download/${data.analysis_id}`, '_blank')
    const handleDocx = () => window.open(`/api/export-docx/${data.analysis_id}`, '_blank')

    const handleValueChange = (key, value) => setComponents(cs => cs.map(c => c.key === key ? { ...c, _editApproved: value } : c))
    const handleJustificationChange = (key, text) => setComponents(cs => cs.map(c => c.key === key ? { ...c, _editJustification: text } : c))

    const handleSaveEdits = async () => {
        setSaving(true); setSaveStatus(null)
        const changed = components.filter(c => c._editApproved !== undefined || c._editJustification !== undefined)
        if (changed.length === 0) { setSaving(false); setSaveStatus('No changes to save.'); return }
        const newLog = []
        for (const comp of changed) {
            const newAmt = comp._editApproved ?? comp.approved
            const newJ = comp._editJustification ?? comp.justification
            try {
                await fetch('/api/override', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ analysis_id: data.analysis_id, component_key: comp.key, new_approved_amount: newAmt, justification: newJ, user_id: 'human_auditor' }),
                })
                newLog.push({ name: comp.name, oldAmt: comp.approved, newAmt, changed: comp._editApproved !== undefined })
            } catch { setSaveStatus('Could not save ' + comp.name) }
        }
        setAuditLog(prev => [...newLog, ...prev])
        setSaveStatus(`${changed.length} component${changed.length > 1 ? 's' : ''} saved. Regenerating the report…`)
        setSaving(false); setEditMode(false)
        setTimeout(() => window.open(`/api/download/${data.analysis_id}`, '_blank'), 800)
    }

    const priorItems = components.filter(c => c.key?.startsWith('prior_period_') && c.approved > 0)
    const lossOver = data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5)
    const dateStr = data.timestamp ? new Date(data.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : ''

    return (
        <section className="stack view">
            <PageHead eyebrow={`Audit report · ${data.licensee_name} · FY ${data.financial_year}${dateStr ? ' · ' + dateStr : ''}`} title="Truing-up decision">
                <button className="btn btn-ghost" onClick={onNewAnalysis}>New analysis</button>
                <button className={`btn ${editMode ? 'is-on' : ''}`} onClick={() => { setEditMode(e => !e); setSaveStatus(null) }}>
                    {editMode ? 'Editing' : 'Edit values'}
                </button>
                {onDraftOrder && <button className="btn" onClick={onDraftOrder}>Draft order</button>}
                <button className="btn" onClick={handleDocx}>Export DOCX</button>
                <button className="btn btn-accent" onClick={handleDownload}>Download PDF</button>
            </PageHead>

            {editMode && (
                <div className="notice notice-info">
                    <span style={{ flex: 1 }}>Edit mode — change approved amounts and observations, then save to regenerate the report.</span>
                    <button className="btn btn-accent btn-sm" disabled={saving} onClick={handleSaveEdits}>{saving ? 'Saving…' : 'Save & regenerate'}</button>
                </div>
            )}
            {saveStatus && <Notice tone="ok" onClose={() => setSaveStatus(null)}>{saveStatus}</Notice>}

            <div className="stats enter-panel">
                <div className="stat"><span className="label">Total claimed</span><div className="stat-value">{fmt(data.total_claimed_expenditure)}</div><div className="stat-unit">Rs. Lakhs</div></div>
                <div className="stat"><span className="label">Total approved</span><div className="stat-value">{fmt(data.total_approved_expenditure)}</div><div className="stat-unit">Rs. Lakhs</div></div>
                <div className="stat"><span className="label">Approved revenue</span><div className="stat-value">{fmt(data.total_approved_revenue)}</div><div className="stat-unit">Rs. Lakhs</div></div>
                <div className="stat">
                    <span className="label">{isSurplus ? 'Revenue surplus' : 'Revenue gap'}</span>
                    <div className={`stat-value ${isSurplus ? 'ok' : 'bad'}`}>{fmt(Math.abs(data.final_revenue_gap_surplus))}</div>
                    <div className="stat-unit">Rs. Lakhs</div>
                </div>
            </div>

            {data.claimed_distribution_loss_pct > 0 && (
                <div className={`notice ${lossOver ? '' : 'notice-ok'}`} style={lossOver ? { borderColor: 'rgba(217,164,65,.3)' } : undefined}>
                    <span>Distribution loss <span className="num">{data.claimed_distribution_loss_pct}%</span>
                        {data.target_distribution_loss_pct > 0 && <span className="faint"> · target <span className="num">{data.target_distribution_loss_pct}%</span></span>}
                        <span className={lossOver ? 'warn' : 'ok'}> · {lossOver ? 'above target' : 'within target'}</span>
                    </span>
                </div>
            )}

            <div className="card enter-panel-2">
                <div className="card-head"><span className="h3">Component analysis</span><span className="spacer" /><span className="label">Rs. Lakhs</span></div>
                <div className="table-wrap">
                    <table className="table">
                        <thead>
                            <tr>
                                <th style={{ width: 48 }}>#</th><th>Particulars</th>
                                <th className="r">MYT norm</th><th className="r">Claimed</th><th className="r">Approved</th><th className="r">Variance</th><th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {components.map((c, i) => (
                                <tr key={c.key}>
                                    <td className="idx">{String(i + 1).padStart(2, '0')}</td>
                                    <td style={{ fontWeight: 500 }}>{c.name}</td>
                                    <td className="r num muted">{c.proposed_myt ? fmt(c.proposed_myt) : '—'}</td>
                                    <td className="r num">{fmt(c.claimed)}</td>
                                    <td className="r num" style={{ fontWeight: 600 }}>
                                        {editMode
                                            ? <input type="number" step="any" className="input input-sm num" style={{ width: 110 }} value={c._editApproved ?? c.approved}
                                                onChange={e => handleValueChange(c.key, parseFloat(e.target.value) || 0)} />
                                            : fmt(c._editApproved ?? c.approved)}
                                    </td>
                                    <td className={`r num ${tone(c.variance)}`}>{signed(c.variance)}</td>
                                    <td><StatusPill status={c.status} /></td>
                                </tr>
                            ))}
                            <tr className="total">
                                <td /><td>Total expenditure</td><td />
                                <td className="r num">{fmt(data.total_claimed_expenditure)}</td>
                                <td className="r num">{fmt(data.total_approved_expenditure)}</td>
                                <td className={`r num ${tone(data.total_approved_expenditure - data.total_claimed_expenditure)}`}>
                                    {signed(data.total_approved_expenditure - data.total_claimed_expenditure)}
                                </td>
                                <td />
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            {priorItems.length > 0 && (
                <div className="card">
                    <div className="card-head"><span className="h3">Prior period costs</span><span className="faint" style={{ fontSize: 12 }}>Arrears from earlier periods found in the petition</span></div>
                    <div className="table-wrap">
                        <table className="table"><tbody>
                            {priorItems.map(item => (
                                <tr key={item.key}><td>{item.name}</td><td className="r num">{fmt(item.approved)}</td><td style={{ width: 140 }}><StatusPill status={item.status} /></td></tr>
                            ))}
                        </tbody></table>
                    </div>
                </div>
            )}

            <CourtHearingEditor analysisId={data.analysis_id} existingData={data.court_hearing} />

            <div className="card">
                <div className="card-head">
                    <span className="h3">Justifications</span>
                    <span className="spacer" />
                    <span className="label">{editMode ? 'Edit mode' : 'Expand a component for the observation'}</span>
                </div>
                <div className="divide">
                    {components.map((c, i) => (
                        <Justification key={c.key} component={c} index={i} editMode={editMode}
                            onValueChange={handleValueChange} onJustificationChange={handleJustificationChange} />
                    ))}
                </div>
            </div>

            {data.disallowances?.length > 0 && (
                <div className="card">
                    <div className="card-head"><span className="h3">Disallowances</span><span className="pill pill-bad">{data.disallowances.length}</span></div>
                    <div className="divide">
                        {data.disallowances.map((d, i) => (
                            <div key={i} className="card-body">
                                <div className="row" style={{ marginBottom: 6 }}>
                                    <span style={{ fontWeight: 500, flex: 1 }}>{d.item}</span>
                                    <span className="num bad">−{fmt(d.amount_cut)}</span>
                                </div>
                                <p className="muted" style={{ lineHeight: 1.7, maxWidth: '90ch' }}>{d.justification}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {auditLog.length > 0 && (
                <div className="card">
                    <div className="card-head"><span className="h3">Override log</span></div>
                    <div className="table-wrap"><table className="table"><tbody>
                        {auditLog.map((e, i) => (
                            <tr key={i}>
                                <td>{e.name}</td>
                                <td className="r num">{e.changed ? `${fmt(e.oldAmt)} → ${fmt(e.newAmt)}` : 'Observation edited'}</td>
                                <td style={{ width: 150 }}><span className="pill pill-accent">Human override</span></td>
                            </tr>
                        ))}
                    </tbody></table></div>
                </div>
            )}
        </section>
    )
}
