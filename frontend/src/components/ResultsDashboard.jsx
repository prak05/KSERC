import { useState } from 'react'

function SummaryCard({ label, value, unit, colorClass, icon }) {
    return (
        <div className="bg-kserc-surface/60 backdrop-blur-2xl rounded-2xl border border-white/10 p-6 shadow-xl hover:shadow-[0_0_25px_rgba(255,255,255,0.05)] hover:-translate-y-1 transition-all duration-300 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            <p className="text-xs font-bold text-white/50 uppercase tracking-widest">{label}</p>
            <p className={`text-3xl font-black mt-3 ${colorClass} drop-shadow-md`}>
                {icon && <span className="mr-2 opacity-80">{icon}</span>}
                {typeof value === 'number' ? value.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : value}
            </p>
            <p className="text-xs text-white/40 mt-2 font-mono">{unit}</p>
        </div>
    )
}

function StatusBadge({ status }) {
    const styles = {
        approved: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]',
        reduced: 'bg-red-500/10 text-red-400 border-red-500/30 shadow-[0_0_10px_rgba(239,68,68,0.2)]',
        increased: 'bg-blue-500/10 text-blue-400 border-blue-500/30 shadow-[0_0_10px_rgba(59,130,246,0.2)]',
    }
    const labels = {
        approved: '✓ Approved',
        reduced: '↓ Reduced',
        increased: '↑ Increased',
    }
    return (
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-[11px] uppercase tracking-wider font-bold border ${styles[status] || 'bg-white/5 text-white/60 border-white/10'}`}>
            {labels[status] || status}
        </span>
    )
}

function JustificationCard({ component, index, editMode, onValueChange, onJustificationChange }) {
    const [expanded, setExpanded] = useState(false)

    const borderColor = component.status === 'reduced'
        ? 'border-l-red-500/50'
        : component.status === 'approved'
            ? 'border-l-emerald-500/50'
            : 'border-l-blue-500/50'

    const bgColor = component.status === 'reduced'
        ? 'bg-red-500/5 hover:bg-red-500/10'
        : component.status === 'approved'
            ? 'bg-emerald-500/5 hover:bg-emerald-500/10'
            : 'bg-blue-500/5 hover:bg-blue-500/10'

    const contentBg = component.status === 'reduced'
        ? 'bg-red-950/20'
        : component.status === 'approved'
            ? 'bg-emerald-950/20'
            : 'bg-blue-950/20'

    const displayApproved = component._editApproved ?? component.approved
    const displayJustification = component._editJustification ?? component.justification

    return (
        <div
            className={`bg-kserc-surface/60 backdrop-blur-xl rounded-xl border border-white/10 border-l-4 ${borderColor} shadow-lg transition-all duration-300 animate-slide-in ${editMode ? 'ring-2 ring-kserc-blue/50 shadow-[0_0_15px_rgba(59,130,246,0.3)]' : ''}`}
            style={{ animationDelay: `${index * 80}ms` }}
        >
            <button
                onClick={() => setExpanded(!expanded)}
                className={`w-full px-6 py-5 flex items-center justify-between text-left transition-colors rounded-r-xl ${bgColor}`}
            >
                <div className="flex items-center gap-4">
                    <span className="text-sm font-black text-white/20 font-mono tracking-widest">{String(index + 1).padStart(2, '0')}</span>
                    <div>
                        <h4 className="font-bold text-white text-base">{component.name}</h4>
                        <div className="flex items-center gap-3 mt-1.5 text-xs text-white/50 font-mono">
                            <span>Claimed: <strong className="text-white/80">₹{component.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></span>
                            <span className="text-white/30">→</span>
                            <span>Approved: <strong className="text-white/80">
                                {editMode
                                    ? <input
                                        type="number" step="any"
                                        value={displayApproved}
                                        onClick={e => e.stopPropagation()}
                                        onChange={e => { e.stopPropagation(); onValueChange(component.key, parseFloat(e.target.value) || 0) }}
                                        className="w-28 text-right bg-black/40 border border-kserc-blue/50 rounded px-2 py-1 text-kserc-blue font-mono focus:outline-none focus:ring-1 focus:ring-kserc-blue shadow-inner"
                                    />
                                    : `₹${displayApproved.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                                }
                            </strong></span>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                    <StatusBadge status={component.status} />
                    <span className={`text-xl text-white/40 transition-transform duration-300 ${expanded ? 'rotate-180 text-white/80' : ''}`}>▾</span>
                </div>
            </button>

            {expanded && (
                <div className={`px-6 pb-6 ${contentBg} border-t border-white/10 rounded-b-xl`}>
                    <div className="pt-6 grid grid-cols-4 gap-4 text-center mb-6">
                        <div className="bg-black/20 rounded-xl px-4 py-4 border border-white/5 backdrop-blur-sm">
                            <p className="text-[10px] uppercase tracking-widest text-white/40 font-bold">MYT Norm</p>
                            <p className="text-xl font-black text-white/90 mt-2 font-mono">₹{(component.proposed_myt || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
                        </div>
                        <div className="bg-black/20 rounded-xl px-4 py-4 border border-white/5 backdrop-blur-sm">
                            <p className="text-[10px] uppercase tracking-widest text-white/40 font-bold">Claimed</p>
                            <p className="text-xl font-black text-white/90 mt-2 font-mono">₹{component.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
                        </div>
                        <div className="bg-black/20 rounded-xl px-4 py-4 border border-white/5 backdrop-blur-sm relative overflow-hidden">
                            <div className="absolute inset-0 bg-kserc-green/5" />
                            <p className="relative z-10 text-[10px] uppercase tracking-widest text-white/40 font-bold">Approved</p>
                            <p className="relative z-10 text-xl font-black text-kserc-green/90 mt-2 font-mono drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]">₹{displayApproved.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
                        </div>
                        <div className="bg-black/20 rounded-xl px-4 py-4 border border-white/5 backdrop-blur-sm">
                            <p className="text-[10px] uppercase tracking-widest text-white/40 font-bold">Variance</p>
                            <p className={`text-xl font-black mt-2 font-mono ${component.variance < 0 ? 'text-kserc-red/90 drop-shadow-[0_0_8px_rgba(239,68,68,0.3)]' : component.variance > 0 ? 'text-kserc-blue/90 drop-shadow-[0_0_8px_rgba(59,130,246,0.3)]' : 'text-white/50'}`}>
                                {component.variance > 0 ? '+' : ''}{component.variance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </p>
                            <p className="text-[10px] text-white/40 font-mono mt-1">
                                ({component.variance_pct > 0 ? '+' : ''}{component.variance_pct}%)
                            </p>
                        </div>
                    </div>

                    <div className="bg-black/30 rounded-xl p-5 border border-white/5 backdrop-blur-sm">
                        <h5 className="text-[11px] font-black uppercase tracking-widest text-white/70 mb-3 flex items-center gap-2">
                            <span>📝</span> Commission's Observation &amp; Justification
                        </h5>
                        {editMode ? (
                            <textarea
                                value={displayJustification}
                                onChange={e => onJustificationChange(component.key, e.target.value)}
                                rows={5}
                                className="w-full text-sm text-white/90 leading-relaxed border border-kserc-blue/30 rounded-lg p-4 bg-black/40 focus:outline-none focus:border-kserc-blue focus:ring-1 focus:ring-kserc-blue resize-y shadow-inner"
                            />
                        ) : (
                            <p className="text-sm text-white/80 leading-relaxed font-light">{displayJustification}</p>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

export default function ResultsDashboard({ data, onNewAnalysis }) {
    const isSurplus = data.final_revenue_gap_surplus >= 0
    const [editMode, setEditMode] = useState(false)
    const [components, setComponents] = useState(data.components || [])
    const [saving, setSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState(null)
    const [auditLog, setAuditLog] = useState([])

    const handleDownload = () => {
        window.open(`/api/download/${data.analysis_id}`, '_blank')
    }

    const handleValueChange = (key, value) => {
        setComponents(comps => comps.map(c =>
            c.key === key ? { ...c, _editApproved: value } : c
        ))
    }

    const handleJustificationChange = (key, text) => {
        setComponents(comps => comps.map(c =>
            c.key === key ? { ...c, _editJustification: text } : c
        ))
    }

    const handleSaveEdits = async () => {
        setSaving(true)
        setSaveStatus(null)
        const changed = components.filter(c =>
            c._editApproved !== undefined || c._editJustification !== undefined
        )
        if (changed.length === 0) {
            setSaving(false)
            setSaveStatus('No changes to save.')
            return
        }
        const newLog = []
        for (const comp of changed) {
            const newAmt = comp._editApproved ?? comp.approved
            const newJ = comp._editJustification ?? comp.justification
            try {
                await fetch('/api/override', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        analysis_id: data.analysis_id,
                        component_key: comp.key,
                        new_approved_amount: newAmt,
                        justification: newJ,
                        user_id: 'human_auditor',
                    }),
                })
                newLog.push({ name: comp.name, oldAmt: comp.approved, newAmt, changed: comp._editApproved !== undefined })
            } catch {
                setSaveStatus('Error saving ' + comp.name)
            }
        }
        setAuditLog(prev => [...newLog, ...prev])
        setSaveStatus(`${changed.length} component(s) saved. Downloading updated PDF…`)
        setSaving(false)
        setEditMode(false)
        setTimeout(() => window.open(`/api/download/${data.analysis_id}`, '_blank'), 800)
    }

    return (
        <section className="space-y-8 animate-fade-in-up">

            {/* ── Header ── */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 pb-6 border-b border-white/10">
                <div>
                    <h2 className="text-3xl font-bold text-white tracking-tight drop-shadow-md">Truing Up Analysis Report</h2>
                    <p className="text-sm font-mono text-white/50 mt-2 uppercase tracking-wide flex items-center gap-3">
                        <span className="px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-white/80">{data.licensee_name}</span>
                        <span>•</span>
                        <span className="px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-white/80">FY {data.financial_year}</span>
                        <span>•</span>
                        <span>{new Date(data.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                    </p>
                </div>
                <div className="flex gap-3 flex-wrap">
                    <button onClick={onNewAnalysis}
                        className="px-5 py-2.5 rounded-xl border border-white/10 bg-black/20 backdrop-blur-md text-sm font-bold text-white/70 hover:text-white hover:bg-white/10 transition-all shadow-lg hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]">
                        ← New Analysis
                    </button>
                    <button
                        onClick={() => { setEditMode(e => !e); setSaveStatus(null) }}
                        className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all border backdrop-blur-md shadow-lg ${editMode
                            ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 hover:bg-amber-500/30'
                            : 'bg-black/20 border-white/10 text-white/70 hover:text-white hover:bg-white/10 hover:shadow-[0_0_15px_rgba(255,255,255,0.1)]'
                            }`}>
                        {editMode ? '✏️ Editing Mode ON' : '✏️ Edit Values'}
                    </button>
                    <button onClick={handleDownload}
                        className="px-5 py-2.5 rounded-xl bg-kserc-blue/20 border border-kserc-blue/50 backdrop-blur-md text-white text-sm font-bold shadow-lg hover:shadow-[0_0_20px_rgba(59,130,246,0.5)] hover:bg-kserc-blue transition-all hover:-translate-y-0.5">
                        ⬇️ Download PDF Order
                    </button>
                </div>
            </div>

            {/* Edit mode banner */}
            {editMode && (
                <div className="bg-amber-500/10 border border-amber-500/30 backdrop-blur-md rounded-xl px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-[0_0_20px_rgba(245,158,11,0.1)]">
                    <p className="text-amber-300 text-sm font-medium flex items-center gap-2">
                        <span className="text-amber-400 animate-pulse">✏️</span> Edit Mode active — click approved amounts or justification text to edit. Click "Save &amp; Re-generate" when done.
                    </p>
                    <button onClick={handleSaveEdits} disabled={saving}
                        className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-white rounded-lg text-sm font-bold transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] whitespace-nowrap hover:-translate-y-0.5">
                        {saving ? '⏳ Saving…' : '✔ Save & Re-generate PDF'}
                    </button>
                </div>
            )}

            {saveStatus && (
                <div className="bg-emerald-500/10 border border-emerald-500/30 backdrop-blur-md shadow-[0_0_15px_rgba(16,185,129,0.1)] rounded-xl px-6 py-4 text-emerald-300 text-sm font-medium flex items-center gap-2">
                    <span>✨</span> {saveStatus}
                </div>
            )}

            {/* ── Summary Cards ── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <SummaryCard
                    label="Total Claimed Expenditure"
                    value={data.total_claimed_expenditure}
                    unit="Rs. Lakhs"
                    colorClass="text-kserc-navy"
                />
                <SummaryCard
                    label="Total Approved Expenditure"
                    value={data.total_approved_expenditure}
                    unit="Rs. Lakhs"
                    colorClass="text-kserc-green"
                    icon="✓"
                />
                <SummaryCard
                    label="Total Revenue"
                    value={data.total_approved_revenue}
                    unit="Rs. Lakhs"
                    colorClass="text-kserc-blue"
                />
                <SummaryCard
                    label={isSurplus ? 'Revenue Surplus' : 'Revenue Gap'}
                    value={Math.abs(data.final_revenue_gap_surplus)}
                    unit="Rs. Lakhs"
                    colorClass={isSurplus ? 'text-kserc-green drop-shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'text-kserc-red drop-shadow-[0_0_10px_rgba(239,68,68,0.3)]'}
                    icon={isSurplus ? '📈' : '📉'}
                />
            </div>

            {/* ── Distribution Loss Alert ── */}
            {data.claimed_distribution_loss_pct > 0 && (
                <div className={`flex items-center gap-4 px-6 py-4 rounded-xl border backdrop-blur-md shadow-lg ${data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5)
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.1)]'
                    : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                    }`}>
                    <span className="text-2xl drop-shadow-md">{data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5) ? '⚠️' : '✅'}</span>
                    <span className="text-sm font-bold tracking-wide">
                        Distribution Loss: <strong className="font-mono text-base">{data.claimed_distribution_loss_pct}%</strong>
                        {data.target_distribution_loss_pct > 0 && (
                            <span className="text-white/50 ml-2 font-mono text-xs">(Target: {data.target_distribution_loss_pct}%)</span>
                        )}
                    </span>
                </div>
            )}

            {/* ── Comparison Table ── */}
            <div className="bg-kserc-surface/60 backdrop-blur-2xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden relative">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                <div className="px-8 py-5 border-b border-white/10 bg-white/5 backdrop-blur-md">
                    <h3 className="font-bold text-white tracking-wide text-lg flex items-center gap-2">
                        <span>📊</span> Component-wise Analysis
                    </h3>
                </div>
                <div className="overflow-x-auto p-4">
                    <table className="w-full text-sm font-mono">
                        <thead>
                            <tr className="text-white/40 text-[10px] uppercase tracking-widest border-b border-white/10">
                                <th className="px-4 py-4 text-left font-bold">Sl.</th>
                                <th className="px-4 py-4 text-left font-bold font-sans">Particulars</th>
                                <th className="px-4 py-4 text-right font-bold">MYT Norm</th>
                                <th className="px-4 py-4 text-right font-bold">Claimed</th>
                                <th className="px-4 py-4 text-right font-bold">Approved</th>
                                <th className="px-4 py-4 text-right font-bold">Variance</th>
                                <th className="px-4 py-4 text-center font-bold">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {components?.map((c, i) => (
                                <tr key={c.key} className={`border-b border-white/5 transition-colors hover:bg-white/5 group relative ${i % 2 === 1 ? 'bg-black/20' : ''}`}>
                                    <td className="px-4 py-4 text-white/30">{String(i + 1).padStart(2, '0')}</td>
                                    <td className="px-4 py-4 font-semibold font-sans text-white/90 group-hover:text-white transition-colors">{c.name}</td>
                                    <td className="px-4 py-4 text-right text-white/40">{c.proposed_myt ? c.proposed_myt.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '-'}</td>
                                    <td className="px-4 py-4 text-right text-white/60">{c.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                    <td className="px-4 py-4 text-right font-bold text-kserc-green/90 group-hover:text-emerald-400 drop-shadow-[0_0_5px_rgba(16,185,129,0.1)] transition-colors">
                                        {editMode
                                            ? <input type="number" step="any"
                                                value={c._editApproved ?? c.approved}
                                                onChange={e => handleValueChange(c.key, parseFloat(e.target.value) || 0)}
                                                className="w-28 text-right bg-black/40 border border-kserc-blue/50 rounded px-2 py-1 text-kserc-blue font-mono focus:outline-none focus:ring-1 focus:ring-kserc-blue"
                                            />
                                            : (c._editApproved ?? c.approved).toLocaleString('en-IN', { minimumFractionDigits: 2 })
                                        }
                                    </td>
                                    <td className={`px-4 py-4 text-right ${c.variance < 0 ? 'text-kserc-red' : c.variance > 0 ? 'text-kserc-blue' : 'text-white/20'}`}>
                                        {c.variance > 0 ? '+' : ''}{c.variance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                    </td>
                                    <td className="px-4 py-4 text-center"><StatusBadge status={c.status} /></td>
                                </tr>
                            ))}

                            {/* Totals row */}
                            <tr className="bg-white/5 font-bold border-t border-white/20 relative">
                                <td className="px-4 py-5"></td>
                                <td className="px-4 py-5 text-white tracking-widest uppercase font-sans text-xs">Total Expenditure</td>
                                <td className="px-4 py-5"></td>
                                <td className="px-4 py-5 text-right text-white/80">{data.total_claimed_expenditure?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                <td className="px-4 py-5 text-right text-emerald-400 drop-shadow-[0_0_8px_rgba(16,185,129,0.3)] text-base">{data.total_approved_expenditure?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                <td className="px-4 py-5 text-right text-red-400">
                                    {(data.total_approved_expenditure - data.total_claimed_expenditure)?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-4 py-5"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            {/* ── Detailed Justifications ── */}
            <div>
                <h3 className="text-2xl font-bold text-white mb-2 drop-shadow-md">
                    Detailed Justifications
                </h3>
                <p className="text-sm text-white/50 mb-6 font-mono">
                    {editMode
                        ? '> EDIT MODE ACTIVE: MODIFY VALUES ABOVE OR JUSTIFICATIONS BELOW'
                        : '> EXPAND COMPONENTS TO VIEW REGULATORY JUSTIFICATIONS'}
                </p>
                <div className="space-y-3">
                    {components?.map((c, i) => (
                        <JustificationCard key={c.key} component={c} index={i}
                            editMode={editMode}
                            onValueChange={handleValueChange}
                            onJustificationChange={handleJustificationChange}
                        />
                    ))}
                </div>
            </div>

            {/* ── Disallowances Summary ── */}
            {data.disallowances?.length > 0 && (
                <div className="bg-red-500/10 rounded-2xl border border-red-500/30 p-8 backdrop-blur-md shadow-[0_0_30px_rgba(239,68,68,0.1)] relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-2 h-full bg-gradient-to-b from-red-500 to-red-600" />
                    <h3 className="text-xl font-bold text-red-400 mb-6 tracking-wide flex items-center gap-3">
                        <span className="text-2xl drop-shadow-[0_0_10px_rgba(239,68,68,0.5)]">⛔</span> Auditing Rules Applied &amp; Disallowances
                    </h3>
                    <div className="space-y-4">
                        {data.disallowances.map((d, i) => (
                            <div key={i} className="bg-black/30 rounded-xl p-5 border border-red-500/20 hover:border-red-500/40 transition-colors backdrop-blur-sm group">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                                    <h4 className="font-semibold text-red-300 text-lg group-hover:text-red-200 transition-colors">
                                        {d.item.includes("Rule Triggered") || d.item.includes("Penalty") ? d.item : `${d.item} Rule Triggered`}
                                    </h4>
                                    <span className="text-sm font-black text-red-500 font-mono bg-red-500/10 px-3 py-1 rounded-md border border-red-500/20 drop-shadow-md">
                                        -₹{d.amount_cut?.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L
                                    </span>
                                </div>
                                <p className="text-sm text-white/70 leading-relaxed font-light"><strong className="text-white/90">Decision: </strong>{d.justification}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── Audit Log of Manual Overrides ── */}
            {auditLog.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/30 backdrop-blur-md rounded-2xl p-6 shadow-lg">
                    <h3 className="text-sm font-black text-amber-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <span>✏️</span> Manual Override Audit Log
                    </h3>
                    <div className="space-y-2">
                        {auditLog.map((entry, i) => (
                            <div key={i} className="bg-black/40 rounded-lg px-4 py-3 border border-amber-500/20 text-sm flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                                <span className="font-bold text-white/90">{entry.name}</span>
                                {entry.changed && (
                                    <span className="text-amber-400 font-mono bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                                        ₹{entry.oldAmt.toFixed(2)} → ₹{entry.newAmt.toFixed(2)} L
                                    </span>
                                )}
                                <span className="text-white/30 text-[10px] uppercase font-bold tracking-widest bg-white/5 px-2 py-1 rounded">Human override</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </section>
    )
}
