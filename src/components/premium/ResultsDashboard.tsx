'use client';

import { useState } from 'react';
import { ChevronDown, Download, FileText, TrendingUp, TrendingDown, CheckCircle, AlertTriangle } from 'lucide-react';
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ComponentData {
    key: string;
    name: string;
    claimed: number;
    approved: number;
    proposed_myt: number;
    variance: number;
    variance_pct: number;
    status: 'approved' | 'reduced' | 'increased';
    justification: string;
    trust_score: number;
    evaluation_metrics: {
        groundedness: number;
        relevance: number;
        context_precision: number;
    };
}

interface ResultsDashboardProps {
    data: {
        analysis_id: string;
        licensee_name: string;
        financial_year: string;
        timestamp: string;
        total_claimed_expenditure: number;
        total_approved_expenditure: number;
        total_approved_revenue: number;
        final_revenue_gap_surplus: number;
        accumulated_surplus: number;
        imputed_interest_on_surplus: number;
        claimed_distribution_loss_pct: number;
        target_distribution_loss_pct: number;
        components: ComponentData[];
        disallowances: Array<{ item: string; claimed: number; approved: number; amount_cut: number; justification: string }>;
    };
    onNewAnalysis: () => void;
}

export default function ResultsDashboard({ data, onNewAnalysis }: ResultsDashboardProps) {
    const isSurplus = data.final_revenue_gap_surplus >= 0;
    const [expandedRow, setExpandedRow] = useState<string | null>(null);

    const handleDownload = () => {
        window.open(`http://localhost:8000/download/${data.analysis_id}`, '_blank');
    };

    return (
        <div className="space-y-8 animate-fade-in-up">
            {/* ── Header ── */}
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 p-8 bg-white rounded-2xl border border-kserc-border shadow-sm">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="border-kserc-gold text-kserc-gold-dark bg-kserc-gold/5 px-3">ARA™ Autonomous Intelligence</Badge>
                        <span className="text-xs text-kserc-text-muted font-mono">{data.analysis_id}</span>
                    </div>
                    <h2 className="text-3xl font-bold text-kserc-navy tracking-tight">ARA Analytical Scrutiny System</h2>
                    <p className="text-sm text-kserc-text-muted mt-2 font-medium">
                        {data.licensee_name} <span className="mx-2">•</span> FY {data.financial_year} <span className="mx-2">•</span> {new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                    </p>
                </div>
                <div className="flex gap-4">
                    <Button variant="outline" onClick={onNewAnalysis} className="rounded-xl border-kserc-border hover:bg-kserc-surface text-kserc-text-muted font-bold">
                        ← New Analysis
                    </Button>
                    <Button onClick={handleDownload} className="bg-gradient-to-r from-kserc-navy to-kserc-blue hover:from-kserc-navy-light hover:to-kserc-blue-light text-white rounded-xl px-6 py-6 h-auto font-bold shadow-lg shadow-kserc-navy/20 gap-2 transition-all hover:scale-[1.02]">
                        <Download size={18} /> Download PDF Order
                    </Button>
                </div>
            </div>

            {/* ── Key Metrics Grid ── */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <MetricCard
                    label="Total Approved Expenditure"
                    value={data.total_approved_expenditure}
                    unit="Rs. Lakhs"
                    trend="positive"
                    icon={<CheckCircle className="text-kserc-green" size={18} />}
                />
                <MetricCard
                    label="Approved Revenue"
                    value={data.total_approved_revenue}
                    unit="Rs. Lakhs"
                    icon={<TrendingUp className="text-kserc-blue" size={18} />}
                />
                <MetricCard
                    label={isSurplus ? "Revenue Surplus" : "Revenue Gap"}
                    value={Math.abs(data.final_revenue_gap_surplus)}
                    unit="Rs. Lakhs"
                    trend={isSurplus ? 'positive' : 'negative'}
                    icon={isSurplus ? <TrendingUp className="text-kserc-green" size={18} /> : <TrendingDown className="text-kserc-red" size={18} />}
                />
            </div>

            {/* ── Regulatory Meta Metrics ── */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-kserc-navy/5 p-6 rounded-2xl border border-kserc-navy/10 flex items-center justify-between">
                    <div>
                        <p className="text-[10px] font-black uppercase tracking-widest text-kserc-navy/60 mb-1">Interest on Surplus (Imputed)</p>
                        <p className="text-2xl font-black text-kserc-navy">₹{data.imputed_interest_on_surplus.toLocaleString('en-IN', { minimumFractionDigits: 2 })} <span className="text-xs font-bold text-kserc-navy/40">Lakhs</span></p>
                        <p className="text-[10px] text-kserc-navy/40 mt-1 font-bold">Calculated at SBI MCLR + 150bps per Reg 32</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-kserc-navy text-white flex items-center justify-center font-black text-xs">SBI%</div>
                </div>
                <div className="bg-kserc-gold/5 p-6 rounded-2xl border border-kserc-gold/20 flex items-center justify-between">
                    <div>
                        <p className="text-[10px] font-black uppercase tracking-widest text-kserc-gold-dark/60 mb-1">Accumulated Surplus Carried Forward</p>
                        <p className="text-2xl font-black text-kserc-gold-dark">₹{data.accumulated_surplus.toLocaleString('en-IN', { minimumFractionDigits: 2 })} <span className="text-xs font-bold text-kserc-gold-dark/40">Lakhs</span></p>
                        <p className="text-[10px] text-kserc-gold-dark/40 mt-1 font-bold">Historical bank of approved surpluses</p>
                    </div>
                    <div className="h-12 w-12 rounded-xl bg-kserc-gold text-white flex items-center justify-center">🏛️</div>
                </div>
            </div>

            {/* ── Distribution Loss Logic ── */}
            {data.claimed_distribution_loss_pct > 0 && (
                <div className={`p-6 rounded-2xl border flex items-start gap-4 transition-all ${data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5)
                    ? 'bg-red-50/50 border-red-200 text-red-900 shadow-sm shadow-red-100'
                    : 'bg-emerald-50/50 border-emerald-200 text-emerald-900'
                    }`}>
                    <div className={`mt-1 p-2 rounded-lg ${data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5) ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
                        {data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5) ? <AlertTriangle size={20} /> : <CheckCircle size={20} />}
                    </div>
                    <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="font-black text-xs uppercase tracking-widest">Distribution Loss Analysis</h4>
                            <Badge className={data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5) ? 'bg-red-600 text-white' : 'bg-emerald-600'}>
                                {data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5) ? 'Penalty Triggered' : 'Within Norms'}
                            </Badge>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 items-end">
                            <div>
                                <p className="text-[10px] font-bold opacity-60 uppercase">Claimed Loss</p>
                                <p className="text-xl font-black">{data.claimed_distribution_loss_pct}%</p>
                            </div>
                            <div>
                                <p className="text-[10px] font-bold opacity-60 uppercase">Regulatory Target</p>
                                <p className="text-xl font-black">{data.target_distribution_loss_pct}%</p>
                            </div>
                            <div className="col-span-2">
                                <p className="text-xs font-medium leading-relaxed opacity-80">
                                    {data.claimed_distribution_loss_pct > (data.target_distribution_loss_pct || 5)
                                        ? "Excess loss of " + (data.claimed_distribution_loss_pct - data.target_distribution_loss_pct).toFixed(2) + "% detected. Power purchase cost disallowed in proportion to excess loss per MYT Reg 14."
                                        : "Licensee has achieved distribution loss targets. Rewards for efficiency may be applicable in the next tariff filing."}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Table: Side-by-Side Comparison ── */}
            <div className="bg-white rounded-2xl border border-kserc-border shadow-sm overflow-hidden">
                <div className="px-8 py-6 border-b border-kserc-border bg-kserc-surface/50 flex items-center justify-between">
                    <h3 className="font-bold text-kserc-navy text-lg flex items-center gap-2">
                        <FileText className="text-kserc-gold" size={20} />
                        ARA Forensic Regulatory Analysis
                    </h3>
                    <div className="flex items-center gap-4 text-xs font-bold uppercase tracking-widest text-kserc-text-muted">
                        <div className="flex items-center gap-1.5"><div className="h-2 w-2 rounded-full bg-kserc-green" /> Approved</div>
                        <div className="flex items-center gap-1.5"><div className="h-2 w-2 rounded-full bg-kserc-red" /> Reduced</div>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm border-collapse">
                        <thead>
                            <tr className="bg-kserc-navy text-white/90 text-[11px] uppercase tracking-wider font-bold">
                                <th className="px-6 py-4 text-left w-16">Sl.</th>
                                <th className="px-6 py-4 text-left">Particulars</th>
                                <th className="px-6 py-4 text-right">MYT Norm</th>
                                <th className="px-6 py-4 text-right">Claimed (₹)</th>
                                <th className="px-6 py-4 text-right">Approved (₹)</th>
                                <th className="px-6 py-4 text-right">Variance</th>
                                <th className="px-6 py-4 text-center">Trust %</th>
                                <th className="px-6 py-4 text-center">Status</th>
                                <th className="px-6 py-4 w-10"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.components.map((c, i) => (
                                <tr
                                    key={c.key}
                                    className={`group border-b border-kserc-border/50 transition-colors hover:bg-kserc-surface/80 cursor-pointer ${expandedRow === c.key ? 'bg-kserc-surface' : ''}`}
                                    onClick={() => setExpandedRow(expandedRow === c.key ? null : c.key)}
                                >
                                    <td className="px-6 py-5 text-kserc-text-muted font-mono text-xs">{i + 1}</td>
                                    <td className="px-6 py-5 font-bold text-kserc-navy">{c.name}</td>
                                    <td className="px-6 py-5 text-right font-mono text-kserc-text-muted italic">₹{c.proposed_myt.toLocaleString('en-IN')}</td>
                                    <td className="px-6 py-5 text-right font-mono text-kserc-text">₹{c.claimed.toLocaleString('en-IN')}</td>
                                    <td className="px-6 py-5 text-right font-mono font-bold text-kserc-navy">₹{c.approved.toLocaleString('en-IN')}</td>
                                    <td className={`px-6 py-5 text-right font-mono font-bold ${c.variance < 0 ? 'text-kserc-red' : c.variance > 0 ? 'text-kserc-blue' : 'text-kserc-green'}`}>
                                        {c.variance > 0 ? '+' : ''}{c.variance.toLocaleString('en-IN')}
                                    </td>
                                    <td className="px-6 py-5 text-center">
                                        <div className="flex flex-col items-center gap-1">
                                            <span className={`text-[11px] font-black ${c.trust_score >= 0.99 ? 'text-emerald-600' : c.trust_score >= 0.95 ? 'text-amber-600' : 'text-red-600'}`}>
                                                {(c.trust_score * 100).toFixed(3)}%
                                            </span>
                                            <div className="h-1 w-12 bg-gray-100 rounded-full overflow-hidden">
                                                <div className="h-full bg-emerald-500" style={{ width: `${c.trust_score * 100}%` }} />
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-5 text-center">
                                        <StatusBadge status={c.status} />
                                    </td>
                                    <td className="px-6 py-5">
                                        <ChevronDown className={`text-kserc-text-muted transition-transform duration-300 ${expandedRow === c.key ? 'rotate-180' : ''}`} size={16} />
                                    </td>
                                </tr>
                            ))}
                            {/* Detailed Justification Dropdown */}
                            {expandedRow && (
                                <tr>
                                    <td colSpan={9} className="px-12 py-8 bg-kserc-surface/50 border-b border-kserc-border">
                                        <div className="animate-fade-in-up grid grid-cols-1 md:grid-cols-3 gap-8">
                                            <div className="md:col-span-2">
                                                <div className="flex items-center gap-2 mb-4">
                                                    <div className="h-1 w-8 bg-kserc-gold rounded-full" />
                                                    <h4 className="text-xs font-black uppercase tracking-widest text-kserc-navy">ARA 'Legal Brain' Observation & Justification</h4>
                                                </div>
                                                <p className="text-sm text-kserc-text leading-relaxed font-medium italic">
                                                    "{data.components.find(c => c.key === expandedRow)?.justification}"
                                                </p>
                                            </div>
                                            <div className="bg-white p-6 rounded-2xl border border-kserc-border shadow-sm">
                                                <div className="flex items-center gap-2 mb-4">
                                                    <AlertTriangle className="text-kserc-gold" size={14} />
                                                    <h4 className="text-[10px] font-black uppercase tracking-widest text-kserc-navy">ARA Precision Evaluation (99.732% Target)</h4>
                                                </div>
                                                <div className="space-y-4">
                                                    <EvalMetric label="Groundedness" value={data.components.find(c => c.key === expandedRow)?.evaluation_metrics.groundedness || 0} />
                                                    <EvalMetric label="Answer Relevance" value={data.components.find(c => c.key === expandedRow)?.evaluation_metrics.relevance || 0} />
                                                    <EvalMetric label="Context Precision" value={data.components.find(c => c.key === expandedRow)?.evaluation_metrics.context_precision || 0} />
                                                </div>
                                                <div className="mt-6 pt-4 border-t border-gray-100 flex items-center justify-between">
                                                    <span className="text-[9px] font-bold text-gray-400 uppercase">Verification Goal</span>
                                                    <span className="text-[10px] font-black text-emerald-600">99.732%</span>
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function EvalMetric({ label, value }: { label: string; value: number }) {
    return (
        <div className="space-y-1.5">
            <div className="flex justify-between items-center text-[10px] uppercase font-bold text-gray-400">
                <span>{label}</span>
                <span className={value >= 0.95 ? 'text-emerald-500' : 'text-amber-500'}>{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1 w-full bg-gray-50 rounded-full overflow-hidden">
                <div
                    className={`h-full transition-all duration-1000 ${value >= 0.95 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                    style={{ width: `${value * 100}%` }}
                />
            </div>
        </div>
    );
}

function MetricCard({ label, value, unit, trend, icon }: { label: string; value: number; unit: string; trend?: 'positive' | 'negative', icon: React.ReactNode }) {
    return (
        <div className="bg-white p-7 rounded-2xl border border-kserc-border shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all group relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                {icon}
            </div>
            <div className="flex flex-col h-full">
                <p className="text-[10px] font-black uppercase tracking-widest text-kserc-text-muted group-hover:text-kserc-navy transition-colors mb-auto">{label}</p>
                <div className="mt-4">
                    <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-black text-kserc-navy tracking-tight">{value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                        <span className="text-[11px] font-bold text-kserc-text-muted">{unit}</span>
                    </div>
                    {trend && (
                        <div className={`flex items-center gap-1 mt-2 text-[10px] font-black uppercase tracking-wider ${trend === 'positive' ? 'text-kserc-green' : 'text-kserc-red'}`}>
                            {trend === 'positive' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                            {trend === 'positive' ? 'Favorable Impact' : 'Negative Impact'}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatusBadge({ status }: { status: 'approved' | 'reduced' | 'increased' }) {
    const styles = {
        approved: 'bg-kserc-green/10 text-kserc-green border-kserc-green/20 ring-kserc-green/5',
        reduced: 'bg-kserc-red/10 text-kserc-red border-kserc-red/20 ring-kserc-red/5',
        increased: 'bg-kserc-blue/10 text-kserc-blue border-kserc-blue/20 ring-kserc-blue/5',
    };
    const labels = {
        approved: 'Approved',
        reduced: 'Reduced',
        increased: 'Increased',
    };
    return (
        <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider border ring-2 ${styles[status]}`}>
            {labels[status]}
        </span>
    );
}
