import { useState } from 'react'
import CourtHearingEditor from './CourtHearingEditor'

function SummaryCard({ label, value, unit, glowColor, icon }) {
    return (
        <div className="glass-card" style={{
            padding: '22px 24px', position: 'relative', overflow: 'hidden',
        }}>
            <div style={{ position: 'absolute', top: -20, right: -20, width: 100, height: 100, background: glowColor || 'var(--accent)', borderRadius: '50%', filter: 'blur(60px)', opacity: 0.08 }} />
            <p className="mono-wide" style={{ marginBottom: 10, position: 'relative' }}>{label}</p>
            <p style={{
                fontFamily: 'var(--font-mono)', fontSize: '1.6rem', fontWeight: 700, color: 'var(--text)',
                fontVariantNumeric: 'tabular-nums', position: 'relative',
            }}>
                {icon && <span style={{ marginRight: 6, fontSize: '1.1rem' }}>{icon}</span>}
                ₹{typeof value === 'number' ? value.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : value}
            </p>
            <p className="mono" style={{ color: 'var(--text-tertiary)', marginTop: 6 }}>{unit}</p>
        </div>
    )
}

function StatusBadge({ status }) {
    const configs = {
        approved: { cls: 'tag-approved', label: '✓ APPROVED' },
        reduced: { cls: 'tag-reduced', label: '↓ REDUCED' },
        increased: { cls: 'tag-modified', label: '↑ INCREASED' },
    }
    const c = configs[status] || { cls: 'tag-neutral', label: status?.toUpperCase() || '-' }
    return <span className={`neon-tag ${c.cls}`}>{c.label}</span>
}

function JustificationCard({ component, index, editMode, onValueChange, onJustificationChange }) {
    const [expanded, setExpanded] = useState(false)
    const displayApproved = component._editApproved ?? component.approved
    const displayJustification = component._editJustification ?? component.justification

    const accentColor = component.status === 'reduced' ? 'var(--red)' : component.status === 'increased' ? 'var(--blue)' : 'var(--green)'

    return (
        <div className="glass-card animate-slide-up" style={{ animationDelay: `${index * 50}ms`, borderLeftWidth: 2, borderLeftColor: accentColor }}>
            <button onClick={() => setExpanded(!expanded)}
                style={{
                    width: '100%', padding: '16px 22px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left',
                }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                    <span className="mono" style={{ color: 'var(--text-tertiary)', fontSize: '10px' }}>{String(index + 1).padStart(2, '0')}</span>
                    <div>
                        <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '0.9rem', letterSpacing: '-0.03em', textTransform: 'none', lineHeight: 1.3, color: 'var(--text)' }}>
                            {component.name}
                        </h4>
                        <div className="mono" style={{ marginTop: 4, display: 'flex', gap: 8, alignItems: 'center', fontSize: '10px' }}>
                            <span>Claimed: <strong style={{ color: 'var(--text)' }}>₹{component.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></span>
                            <span style={{ color: 'var(--text-tertiary)' }}>→</span>
                            <span>Approved: <strong style={{ color: accentColor }}>
                                {editMode
                                    ? <input type="number" step="any" value={displayApproved}
                                        onClick={e => e.stopPropagation()}
                                        onChange={e => { e.stopPropagation(); onValueChange(component.key, parseFloat(e.target.value) || 0) }}
                                        className="neon-input" style={{ width: 90, fontSize: '10px', padding: '3px 6px', fontFamily: 'var(--font-mono)' }} />
                                    : `₹${displayApproved.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                                }
                            </strong></span>
                        </div>
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <StatusBadge status={component.status} />
                    <span style={{ color: 'var(--text-tertiary)', fontSize: '12px', transition: 'transform 0.2s', transform: expanded ? 'rotate(180deg)' : 'none' }}>▾</span>
                </div>
            </button>

            {expanded && (
                <div style={{ padding: '0 22px 22px', borderTop: '1px solid var(--border)' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, margin: '16px 0' }}>
                        {[
                            { label: 'MYT Norm', val: component.proposed_myt || 0 },
                            { label: 'Claimed', val: component.claimed },
                            { label: 'Approved', val: displayApproved, color: 'var(--green)' },
                            { label: 'Variance', val: component.variance, prefix: component.variance > 0 ? '+' : '', color: component.variance < 0 ? 'var(--red)' : component.variance > 0 ? 'var(--blue)' : 'var(--text-tertiary)' },
                        ].map((m, i) => (
                            <div key={i} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px 14px', textAlign: 'center' }}>
                                <p className="mono-wide" style={{ fontSize: '8px', marginBottom: 6 }}>{m.label}</p>
                                <p style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: m.color || 'var(--text)', fontSize: '0.95rem', fontVariantNumeric: 'tabular-nums' }}>
                                    ₹{(m.prefix || '')}{m.val.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                </p>
                                {m.label === 'Variance' && (
                                    <p className="mono" style={{ color: 'var(--text-tertiary)', marginTop: 2, fontSize: '9px' }}>
                                        ({component.variance_pct > 0 ? '+' : ''}{component.variance_pct}%)
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '16px 18px' }}>
                        <p className="mono-wide" style={{ fontSize: '8px', marginBottom: 8 }}>⚖️ Commission's Observation</p>
                        {editMode ? (
                            <textarea value={displayJustification} onChange={e => onJustificationChange(component.key, e.target.value)}
                                rows={4} className="neon-input" style={{ width: '100%', resize: 'vertical', fontFamily: 'var(--font-body)', fontSize: '0.8rem', lineHeight: 1.6 }} />
                        ) : (
                            <p style={{ fontSize: '0.8rem', lineHeight: 1.7, color: 'rgba(255,255,255,0.6)' }}>{displayJustification}</p>
                        )}
                    </div>
                </div>
            )}
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

    const handleValueChange = (key, value) => {
        setComponents(comps => comps.map(c => c.key === key ? { ...c, _editApproved: value } : c))
    }

    const handleJustificationChange = (key, text) => {
        setComponents(comps => comps.map(c => c.key === key ? { ...c, _editJustification: text } : c))
    }

    const handleSaveEdits = async () => {
        setSaving(true); setSaveStatus(null)
        const changed = components.filter(c => c._editApproved !== undefined || c._editJustification !== undefined)
        if (changed.length === 0) { setSaving(false); setSaveStatus('No changes.'); return }
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
            } catch { setSaveStatus('Error saving ' + comp.name) }
        }
        setAuditLog(prev => [...newLog, ...prev])
        setSaveStatus(`${changed.length} component(s) saved. Downloading PDF…`)
        setSaving(false); setEditMode(false)
        setTimeout(() => window.open(`/api/download/${data.analysis_id}`, '_blank'), 800)
    }

    return (
        <section className="animate-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

            {/* Header */}
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, borderBottom: '1px solid var(--border)', paddingBottom: 20 }}>
                <div>
                    <h2 style={{ fontSize: 'clamp(1.4rem, 3vw, 2rem)', letterSpacing: '-0.05em', marginBottom: 10 }}>Audit Report</h2>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <span className="neon-tag tag-neutral">{data.licensee_name}</span>
                        <span className="neon-tag tag-neutral">FY {data.financial_year}</span>
                        <span className="neon-tag tag-neutral">{new Date(data.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button onClick={onNewAnalysis} className="ghost-btn">← New Analysis</button>
                    <button onClick={() => { setEditMode(e => !e); setSaveStatus(null) }}
                        className={`ghost-btn ${editMode ? 'ghost-btn-accent' : ''}`}
                        style={editMode ? { color: 'var(--accent)', borderColor: 'var(--border-accent)' } : {}}>
                        {editMode ? '🖊️ Editing ON' : '🖊️ Edit'}
                    </button>
                    {onDraftOrder && (
                        <button onClick={onDraftOrder} className="ghost-btn" style={{ borderColor: 'rgba(0,255,136,0.3)' }}>
                            📄 Draft Order
                        </button>
                    )}
                    <button onClick={handleDownload} className="laser-btn" style={{ fontSize: '0.7rem', padding: '10px 20px' }}>
                        📥 Download PDF
                    </button>
                </div>
            </div>

            {/* Edit banner */}
            {editMode && (
                <div className="glass-card" style={{ borderColor: 'var(--border-accent)', padding: '14px 22px', display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                    <p className="mono" style={{ color: 'var(--accent)' }}>🖊️ EDIT MODE — Modify values & justifications</p>
                    <button onClick={handleSaveEdits} disabled={saving} className="laser-btn" style={{ fontSize: '0.65rem', padding: '8px 18px', opacity: saving ? 0.5 : 1 }}>
                        {saving ? '⏳ Saving…' : '💾 Save & Re-generate'}
                    </button>
                </div>
            )}
            {saveStatus && (
                <div className="glass-card" style={{ borderColor: 'rgba(0,255,136,0.3)', padding: '12px 18px' }}>
                    <p className="mono" style={{ color: 'var(--green)' }}>🟢 {saveStatus}</p>
                </div>
            )}

            {/* Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
                <SummaryCard label="Total Claimed" value={data.total_claimed_expenditure} unit="Rs. Lakhs" />
                <SummaryCard label="Total Approved" value={data.total_approved_expenditure} unit="Rs. Lakhs" icon="✓" glowColor="var(--green)" />
                <SummaryCard label="Total Revenue" value={data.total_approved_revenue} unit="Rs. Lakhs" glowColor="var(--blue)" />
                <SummaryCard label={isSurplus ? 'Revenue Surplus' : 'Revenue Gap'} value={Math.abs(data.final_revenue_gap_surplus)} unit="Rs. Lakhs" icon={isSurplus ? '🟩' : '🟥'} glowColor={isSurplus ? 'var(--green)' : 'var(--red)'} />
            </div>

            {/* Distribution Loss */}
            {data.claimed_distribution_loss_pct > 0 && (
                <div className="glass-card" style={{
                    borderColor: data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5) ? 'rgba(255,136,68,0.3)' : 'rgba(0,255,136,0.3)',
                    padding: '14px 22px', display: 'flex', alignItems: 'center', gap: 12,
                }}>
                    <span style={{ fontSize: '1.2rem' }}>{data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5) ? '⚠️' : '✅'}</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                        Distribution Loss: <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.95rem', fontVariantNumeric: 'tabular-nums' }}>{data.claimed_distribution_loss_pct}%</span>
                        {data.target_distribution_loss_pct > 0 && (
                            <span className="mono" style={{ marginLeft: 10 }}>(Target: {data.target_distribution_loss_pct}%)</span>
                        )}
                    </span>
                </div>
            )}

            {/* Court Hearing Details */}
            <CourtHearingEditor
                analysisId={data.analysis_id}
                existingData={data.court_hearing}
            />

            {/* Comparison Table */}
            <div className="glass-card" style={{ overflow: 'hidden' }}>
                <div style={{ background: 'rgba(191, 255, 0, 0.05)', borderBottom: '1px solid var(--border)', padding: '14px 22px', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="mono-wide" style={{ color: 'var(--accent)' }}>🔬 Component Analysis</span>
                </div>
                <div style={{ overflowX: 'auto' }}>
                    <table className="neon-table">
                        <thead>
                            <tr>
                                <th style={{ width: 50 }}>Sl.</th>
                                <th>Particulars</th>
                                <th style={{ textAlign: 'right' }}>MYT Norm</th>
                                <th style={{ textAlign: 'right' }}>Claimed</th>
                                <th style={{ textAlign: 'right' }}>Approved</th>
                                <th style={{ textAlign: 'right' }}>Variance</th>
                                <th style={{ textAlign: 'center' }}>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {components?.map((c, i) => (
                                <tr key={c.key}>
                                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>{String(i + 1).padStart(2, '0')}</td>
                                    <td style={{ fontWeight: 500 }}>{c.name}</td>
                                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                                        {c.proposed_myt ? c.proposed_myt.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '—'}
                                    </td>
                                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                                        {c.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                    </td>
                                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--green)' }}>
                                        {editMode
                                            ? <input type="number" step="any" value={c._editApproved ?? c.approved}
                                                onChange={e => handleValueChange(c.key, parseFloat(e.target.value) || 0)}
                                                className="neon-input" style={{ width: 90, textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', padding: '4px 6px' }} />
                                            : (c._editApproved ?? c.approved).toLocaleString('en-IN', { minimumFractionDigits: 2 })
                                        }
                                    </td>
                                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', color: c.variance < 0 ? 'var(--red)' : c.variance > 0 ? 'var(--blue)' : 'var(--text-tertiary)' }}>
                                        {c.variance > 0 ? '+' : ''}{c.variance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                    </td>
                                    <td style={{ textAlign: 'center' }}><StatusBadge status={c.status} /></td>
                                </tr>
                            ))}
                            <tr style={{ background: 'rgba(191,255,0,0.05)' }}>
                                <td></td>
                                <td className="mono-wide" style={{ color: 'var(--accent)' }}>Total Expenditure</td>
                                <td></td>
                                <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                                    {data.total_claimed_expenditure?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent)', fontSize: '0.9rem' }}>
                                    {data.total_approved_expenditure?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                </td>
                                <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                                    {(data.total_approved_expenditure - data.total_claimed_expenditure)?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                </td>
                                <td></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Prior Period Costs — shown only if petition has prior period items */}
            {(() => {
                const priorItems = components?.filter(c => c.key?.startsWith('prior_period_') && c.approved > 0) || []
                if (priorItems.length === 0) return null
                return (
                    <div className="glass-card animate-slide-up" style={{ overflow: 'hidden', borderColor: 'rgba(180, 130, 255, 0.3)', borderWidth: 1.5 }}>
                        <div style={{
                            background: 'linear-gradient(135deg, rgba(180,130,255,0.08), rgba(120,80,255,0.04))',
                            borderBottom: '1px solid rgba(180,130,255,0.2)',
                            padding: '16px 22px',
                            display: 'flex', alignItems: 'center', gap: 10,
                        }}>
                            <span style={{ fontSize: '1.2rem' }}>📋</span>
                            <div>
                                <span className="mono-wide" style={{ color: '#b482ff', fontSize: '10px' }}>
                                    PRIOR PERIOD COSTS
                                </span>
                                <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                                    Costs from previous periods found in the petition (e.g., wage revision arrears)
                                </p>
                            </div>
                        </div>
                        <div style={{ padding: '16px 22px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
                                {priorItems.map((item, i) => (
                                    <div key={i} style={{
                                        background: 'rgba(180,130,255,0.04)',
                                        border: '1px solid rgba(180,130,255,0.15)',
                                        borderRadius: 'var(--radius-sm)',
                                        padding: '16px 18px',
                                    }}>
                                        <p className="mono-wide" style={{ fontSize: '8px', marginBottom: 8, color: '#b482ff' }}>
                                            {item.name}
                                        </p>
                                        <p style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1.1rem', color: '#b482ff', fontVariantNumeric: 'tabular-nums' }}>
                                            ₹{item.approved.toLocaleString('en-IN', { minimumFractionDigits: 2 })}L
                                        </p>
                                        <p className="mono" style={{ color: 'var(--text-tertiary)', marginTop: 6, fontSize: '9px' }}>
                                            {item.status === 'approved' ? '✓ Approved' : item.status === 'increased' ? '↑ Added by Commission' : item.status}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )
            })()}

            {/* Justifications */}
            <div>
                <h3 style={{ fontSize: '1.3rem', letterSpacing: '-0.04em', marginBottom: 4 }}>Justifications</h3>
                <p className="mono" style={{ color: 'var(--text-tertiary)', marginBottom: 16 }}>
                    {editMode ? '> EDIT MODE ACTIVE' : '> EXPAND TO VIEW OBSERVATIONS'}
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {components?.map((c, i) => (
                        <JustificationCard key={c.key} component={c} index={i} editMode={editMode}
                            onValueChange={handleValueChange} onJustificationChange={handleJustificationChange} />
                    ))}
                </div>
            </div>

            {/* Disallowances */}
            {data.disallowances?.length > 0 && (
                <div className="glass-card" style={{ overflow: 'hidden', borderColor: 'rgba(255,68,68,0.3)' }}>
                    <div style={{ background: 'var(--red-dim)', borderBottom: '1px solid rgba(255,68,68,0.2)', padding: '14px 22px' }}>
                        <span className="mono-wide" style={{ color: 'var(--red)' }}>🚫 Disallowances</span>
                    </div>
                    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {data.disallowances.map((d, i) => (
                            <div key={i} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px 18px' }}>
                                <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                                    <h4 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '0.85rem', color: 'var(--red)', textTransform: 'none', lineHeight: 1.3 }}>{d.item}</h4>
                                    <span className="neon-tag tag-reduced" style={{ fontSize: '10px' }}>
                                        -₹{d.amount_cut?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}L
                                    </span>
                                </div>
                                <p style={{ fontSize: '0.8rem', lineHeight: 1.7, color: 'rgba(255,255,255,0.6)' }}>
                                    <strong style={{ color: 'var(--text)' }}>Decision: </strong>{d.justification}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Audit Log */}
            {auditLog.length > 0 && (
                <div className="glass-card" style={{ borderColor: 'var(--border-accent)', padding: '18px 22px' }}>
                    <p className="mono-wide" style={{ color: 'var(--accent)', marginBottom: 12, fontSize: '9px' }}>📋 Override Log</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {auditLog.map((entry, i) => (
                            <div key={i} style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '10px 14px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                                <span style={{ fontWeight: 500, fontSize: '0.8rem' }}>{entry.name}</span>
                                {entry.changed && <span className="mono" style={{ color: 'var(--accent)' }}>₹{entry.oldAmt.toFixed(2)} → ₹{entry.newAmt.toFixed(2)}</span>}
                                <span className="neon-tag tag-neutral" style={{ fontSize: '8px' }}>Human Override</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </section>
    )
}
