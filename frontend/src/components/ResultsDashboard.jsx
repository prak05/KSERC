import { useState } from 'react'

function SummaryCard({ label, value, unit, colorClass, icon }) {
    return (
        <div className="bg-white rounded-xl border border-kserc-border p-5 shadow-sm hover:shadow-md transition-shadow">
            <p className="text-xs font-semibold text-kserc-text-muted uppercase tracking-wider">{label}</p>
            <p className={`text-2xl font-bold mt-2 ${colorClass}`}>
                {icon && <span className="mr-1">{icon}</span>}
                {typeof value === 'number' ? value.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : value}
            </p>
            <p className="text-xs text-kserc-text-muted mt-1">{unit}</p>
        </div>
    )
}

function StatusBadge({ status }) {
    const styles = {
        approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        reduced: 'bg-red-50 text-red-700 border-red-200',
        increased: 'bg-blue-50 text-blue-700 border-blue-200',
    }
    const labels = {
        approved: '✓ Approved',
        reduced: '↓ Reduced',
        increased: '↑ Increased',
    }
    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles[status] || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
            {labels[status] || status}
        </span>
    )
}

function JustificationCard({ component, index }) {
    const [expanded, setExpanded] = useState(false)

    const borderColor = component.status === 'reduced'
        ? 'border-l-red-400'
        : component.status === 'approved'
            ? 'border-l-emerald-400'
            : 'border-l-blue-400'

    const bgColor = component.status === 'reduced'
        ? 'bg-red-50/30'
        : component.status === 'approved'
            ? 'bg-emerald-50/30'
            : 'bg-blue-50/30'

    return (
        <div
            className={`bg-white rounded-lg border border-kserc-border border-l-4 ${borderColor} shadow-sm transition-all duration-300 animate-slide-in`}
            style={{ animationDelay: `${index * 80}ms` }}
        >
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-gray-50/50 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <span className="text-sm font-bold text-kserc-navy/50">{String(index + 1).padStart(2, '0')}</span>
                    <div>
                        <h4 className="font-semibold text-kserc-navy">{component.name}</h4>
                        <div className="flex items-center gap-4 mt-1 text-xs text-kserc-text-muted">
                            <span>Claimed: <strong className="text-kserc-text">₹{component.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L</strong></span>
                            <span>→</span>
                            <span>Approved: <strong className="text-kserc-text">₹{component.approved.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L</strong></span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <StatusBadge status={component.status} />
                    <span className={`text-lg transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}>▾</span>
                </div>
            </button>

            {expanded && (
                <div className={`px-5 pb-5 ${bgColor} border-t border-kserc-border/50`}>
                    <div className="pt-4 grid grid-cols-4 gap-4 text-center mb-4">
                        <div className="bg-white rounded-lg px-4 py-3 border border-kserc-border/50">
                            <p className="text-[10px] uppercase tracking-wider text-kserc-text-muted font-semibold">MYT Norm</p>
                            <p className="text-lg font-bold text-kserc-navy mt-1">₹{(component.proposed_myt || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
                            <p className="text-[10px] text-kserc-text-muted">Rs. Lakhs</p>
                        </div>
                        <div className="bg-white rounded-lg px-4 py-3 border border-kserc-border/50">
                            <p className="text-[10px] uppercase tracking-wider text-kserc-text-muted font-semibold">Claimed</p>
                            <p className="text-lg font-bold text-kserc-navy mt-1">₹{component.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
                            <p className="text-[10px] text-kserc-text-muted">Rs. Lakhs</p>
                        </div>
                        <div className="bg-white rounded-lg px-4 py-3 border border-kserc-border/50">
                            <p className="text-[10px] uppercase tracking-wider text-kserc-text-muted font-semibold">Approved</p>
                            <p className="text-lg font-bold text-kserc-green mt-1">₹{component.approved.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
                            <p className="text-[10px] text-kserc-text-muted">Rs. Lakhs</p>
                        </div>
                        <div className="bg-white rounded-lg px-4 py-3 border border-kserc-border/50">
                            <p className="text-[10px] uppercase tracking-wider text-kserc-text-muted font-semibold">Variance</p>
                            <p className={`text-lg font-bold mt-1 ${component.variance < 0 ? 'text-kserc-red' : component.variance > 0 ? 'text-kserc-blue' : 'text-kserc-text-muted'}`}>
                                {component.variance > 0 ? '+' : ''}{component.variance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </p>
                            <p className="text-[10px] text-kserc-text-muted">
                                ({component.variance_pct > 0 ? '+' : ''}{component.variance_pct}%)
                            </p>
                        </div>
                    </div>

                    <div className="bg-white rounded-lg p-4 border border-kserc-border/50">
                        <h5 className="text-xs font-bold uppercase tracking-wider text-kserc-navy mb-2">
                            Commission's Observation & Justification
                        </h5>
                        <p className="text-sm text-kserc-text leading-relaxed">{component.justification}</p>
                    </div>
                </div>
            )}
        </div>
    )
}

export default function ResultsDashboard({ data, onNewAnalysis }) {
    const isSurplus = data.final_revenue_gap_surplus >= 0

    const handleDownload = () => {
        window.open(`/api/download/${data.analysis_id}`, '_blank')
    }

    return (
        <section className="space-y-8 animate-fade-in-up">

            {/* ── Header ── */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-kserc-navy">Truing Up Analysis Report</h2>
                    <p className="text-sm text-kserc-text-muted mt-1">
                        {data.licensee_name} • FY {data.financial_year} • {new Date(data.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={onNewAnalysis}
                        className="px-5 py-2.5 rounded-lg border border-kserc-border text-sm font-medium text-kserc-text-muted hover:bg-gray-50 transition-colors"
                    >
                        ← New Analysis
                    </button>
                    <button
                        onClick={handleDownload}
                        className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-kserc-navy to-kserc-blue text-white text-sm font-bold shadow-md hover:shadow-lg transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                        ⬇️ Download PDF Order
                    </button>
                </div>
            </div>

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
                    colorClass={isSurplus ? 'text-kserc-green' : 'text-kserc-red'}
                    icon={isSurplus ? '📈' : '📉'}
                />
            </div>

            {/* ── Distribution Loss Alert ── */}
            {data.claimed_distribution_loss_pct > 0 && (
                <div className={`flex items-center gap-3 px-5 py-3.5 rounded-lg border ${data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5)
                    ? 'bg-amber-50 border-amber-200 text-amber-800'
                    : 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    }`}>
                    <span className="text-xl">{data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5) ? '⚠️' : '✅'}</span>
                    <span className="text-sm font-medium">
                        Distribution Loss: <strong>{data.claimed_distribution_loss_pct}%</strong>
                        {data.target_distribution_loss_pct > 0 && (
                            <> (Target: {data.target_distribution_loss_pct}%)</>
                        )}
                    </span>
                </div>
            )}

            {/* ── Comparison Table ── */}
            <div className="bg-white rounded-xl border border-kserc-border shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-kserc-border bg-kserc-navy/[0.02]">
                    <h3 className="font-bold text-kserc-navy">Component-wise Analysis</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-kserc-navy text-white text-xs uppercase tracking-wider">
                                <th className="px-4 py-3 text-left w-12">Sl.</th>
                                <th className="px-4 py-3 text-left">Particulars</th>
                                <th className="px-4 py-3 text-right">MYT Norm</th>
                                <th className="px-4 py-3 text-right">Claimed (₹ Lakhs)</th>
                                <th className="px-4 py-3 text-right">Approved (₹ Lakhs)</th>
                                <th className="px-4 py-3 text-right">Variance</th>
                                <th className="px-4 py-3 text-center">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.components?.map((c, i) => (
                                <tr key={c.key} className={`border-b border-kserc-border/50 transition-colors hover:bg-kserc-navy/[0.02] ${i % 2 === 1 ? 'bg-gray-50/50' : ''}`}>
                                    <td className="px-4 py-3 text-kserc-text-muted font-mono">{i + 1}</td>
                                    <td className="px-4 py-3 font-medium text-kserc-navy">{c.name}</td>
                                    <td className="px-4 py-3 text-right font-mono text-kserc-text-muted">{c.proposed_myt ? c.proposed_myt.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '-'}</td>
                                    <td className="px-4 py-3 text-right font-mono">{c.claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                    <td className="px-4 py-3 text-right font-mono font-semibold">{c.approved.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                    <td className={`px-4 py-3 text-right font-mono ${c.variance < 0 ? 'text-kserc-red' : c.variance > 0 ? 'text-kserc-blue' : ''}`}>
                                        {c.variance > 0 ? '+' : ''}{c.variance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                    </td>
                                    <td className="px-4 py-3 text-center"><StatusBadge status={c.status} /></td>
                                </tr>
                            ))}

                            {/* Totals row */}
                            <tr className="bg-kserc-navy/5 font-bold border-t-2 border-kserc-navy/20">
                                <td className="px-4 py-3"></td>
                                <td className="px-4 py-3 text-kserc-navy">TOTAL EXPENDITURE</td>
                                <td className="px-4 py-3"></td>
                                <td className="px-4 py-3 text-right font-mono">{data.total_claimed_expenditure?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                <td className="px-4 py-3 text-right font-mono text-kserc-green">{data.total_approved_expenditure?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                <td className="px-4 py-3 text-right font-mono text-kserc-red">
                                    {(data.total_approved_expenditure - data.total_claimed_expenditure)?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-4 py-3"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            {/* ── Detailed Justifications ── */}
            <div>
                <h3 className="text-xl font-bold text-kserc-navy mb-4">
                    Detailed Justifications & Commission's Observations
                </h3>
                <p className="text-sm text-kserc-text-muted mb-6">
                    Click on each component to view the detailed regulatory justification for the approval or adjustment.
                </p>
                <div className="space-y-3">
                    {data.components?.map((c, i) => (
                        <JustificationCard key={c.key} component={c} index={i} />
                    ))}
                </div>
            </div>

            {/* ── Disallowances Summary ── */}
            {data.disallowances?.length > 0 && (
                <div className="bg-red-50/50 rounded-xl border border-red-200 p-6">
                    <h3 className="text-lg font-bold text-kserc-red mb-4">⛔ Auditing Rules Applied & Disallowances</h3>
                    <div className="space-y-3">
                        {data.disallowances.map((d, i) => (
                            <div key={i} className="bg-white rounded-lg p-4 border border-red-200/50">
                                <div className="flex items-center justify-between mb-2">
                                    <h4 className="font-semibold text-kserc-red">
                                        {d.item.includes("Rule Triggered") || d.item.includes("Penalty") ? d.item : `${d.item} Rule Triggered`}
                                    </h4>
                                    <span className="text-sm font-bold text-kserc-red">
                                        -₹{d.amount_cut?.toLocaleString('en-IN', { minimumFractionDigits: 2 })} Lakhs
                                    </span>
                                </div>
                                <p className="text-sm text-kserc-text leading-relaxed"><strong>Decision: </strong>{d.justification}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </section>
    )
}
