'use client';

import { useState } from 'react';
import { AlertCircle, ThumbsUp, Edit3, Loader2 } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ReviewSummary {
    licensee: string;
    financial_year: string;
    total_claimed: number;
    total_approved: number;
    total_revenue: number;
    gap_surplus: number;
    disallowances: Array<{ item: string; claimed: number; approved: number; amount_cut: number; justification: string }>;
}

interface ReviewModalProps {
    summary: ReviewSummary;
    onReviewSubmit: (approve: boolean, overrideText?: string) => void;
    isSubmitting: boolean;
}

export default function PremiumReviewModal({ summary, onReviewSubmit, isSubmitting }: ReviewModalProps) {
    const [overrideText, setOverrideText] = useState("");

    return (
        <div className="max-w-4xl mx-auto space-y-8 animate-fade-in-up pb-20">
            <div className="flex items-center gap-4 p-6 bg-kserc-amber/5 border border-kserc-amber/20 rounded-2xl">
                <div className="h-12 w-12 rounded-xl bg-kserc-amber/10 flex items-center justify-center text-kserc-amber shrink-0">
                    <AlertCircle size={24} />
                </div>
                <div>
                    <h3 className="text-lg font-black text-kserc-navy tracking-tight">Human-in-the-Loop Review Required</h3>
                    <p className="text-sm text-kserc-text-muted font-medium mt-0.5">The AI pipeline has paused at a critical decision gate. Please evaluate the audit findings.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <SummaryItem label="Total Claimed" value={summary.total_claimed} />
                <SummaryItem label="Total Approved" value={summary.total_approved} highlight="green" />
                <SummaryItem label="Total Revenue" value={summary.total_revenue} highlight="blue" />
                <SummaryItem
                    label={summary.gap_surplus >= 0 ? "Potential Surplus" : "Potential Gap"}
                    value={Math.abs(summary.gap_surplus)}
                    highlight={summary.gap_surplus >= 0 ? "green" : "red"}
                />
            </div>

            <Card className="rounded-2xl border-kserc-border shadow-sm overflow-hidden">
                <CardHeader className="bg-kserc-surface/50 border-b border-kserc-border py-4">
                    <CardTitle className="text-xs font-black uppercase tracking-widest text-kserc-navy">Critical Audit Observations ({summary.disallowances.length})</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="divide-y divide-kserc-border text-sm">
                        {summary.disallowances.map((d, i) => (
                            <div key={i} className="px-8 py-5 hover:bg-kserc-surface/30 transition-colors">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="font-bold text-kserc-navy">{d.item}</span>
                                    <Badge variant="destructive" className="bg-kserc-red/10 text-kserc-red border-kserc-red/20 text-[10px] font-black uppercase tracking-widest">
                                        −₹{d.amount_cut.toFixed(2)} L
                                    </Badge>
                                </div>
                                <p className="text-[12px] text-kserc-text-muted leading-relaxed italic">"{d.justification}"</p>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            <div className="bg-white p-8 rounded-2xl border-2 border-kserc-navy/10 shadow-xl space-y-8">
                <div className="space-y-2">
                    <h4 className="text-lg font-black text-kserc-navy tracking-tight">Final Decision</h4>
                    <p className="text-xs text-kserc-text-muted font-medium">Approve the AI audit findings as-is or provide specific regulatory overrides.</p>
                </div>

                <div className="flex flex-col md:flex-row gap-4">
                    <Button
                        onClick={() => onReviewSubmit(true)}
                        disabled={isSubmitting}
                        className="flex-1 bg-kserc-green hover:bg-kserc-green-light text-white rounded-xl h-16 font-black text-lg gap-2 shadow-lg shadow-kserc-green/20"
                    >
                        {isSubmitting ? <Loader2 className="animate-spin" /> : <ThumbsUp size={20} />} Approve Findings
                    </Button>

                    <div className="flex-[2] flex gap-2">
                        <input
                            className="flex-1 rounded-xl border-kserc-border bg-kserc-surface px-6 text-sm font-medium focus:ring-kserc-navy focus:border-kserc-navy transition-all"
                            placeholder="Enter specific override instruction (e.g., 'Allow Rs 10L for...')"
                            value={overrideText}
                            onChange={(e) => setOverrideText(e.target.value)}
                        />
                        <Button
                            variant="outline"
                            disabled={!overrideText.trim() || isSubmitting}
                            onClick={() => onReviewSubmit(false, overrideText)}
                            className="rounded-xl border-kserc-navy text-kserc-navy h-16 px-6 font-bold hover:bg-kserc-navy hover:text-white transition-all gap-2"
                        >
                            <Edit3 size={18} /> Apply Override
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}

function SummaryItem({ label, value, highlight }: { label: string; value: number; highlight?: 'green' | 'blue' | 'red' }) {
    const colorMap = {
        green: 'text-kserc-green',
        blue: 'text-kserc-blue',
        red: 'text-kserc-red',
        none: 'text-kserc-navy'
    };
    return (
        <div className="bg-white p-5 rounded-2xl border border-kserc-border shadow-sm">
            <p className="text-[9px] font-black uppercase tracking-widest text-kserc-text-muted mb-2">{label}</p>
            <div className="flex items-baseline gap-1.5">
                <span className={`text-xl font-black tracking-tight ${colorMap[highlight || 'none']}`}>₹{value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                <span className="text-[10px] font-bold text-kserc-text-muted">L</span>
            </div>
        </div>
    );
}
