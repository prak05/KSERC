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

export default function ReviewModal({ summary, onReviewSubmit, isSubmitting }: ReviewModalProps) {
    const [overrideText, setOverrideText] = useState("");

    return (
        <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
            <div className="flex items-center gap-4 p-6 bg-amber-50 border border-amber-200 rounded-2xl">
                <div className="h-12 w-12 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600 shrink-0">
                    <AlertCircle size={24} />
                </div>
                <div>
                    <h3 className="text-lg font-bold text-navy tracking-tight">Human-in-the-Loop Review Required</h3>
                    <p className="text-sm text-muted-foreground font-medium mt-0.5">The AI pipeline has paused at a critical decision gate. Please evaluate the audit findings.</p>
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

            <Card className="rounded-2xl border-slate-200 shadow-sm overflow-hidden">
                <CardHeader className="bg-slate-50 border-b border-slate-200 py-4">
                    <CardTitle className="text-xs font-bold uppercase tracking-widest text-navy">Critical Audit Observations ({summary.disallowances.length})</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="divide-y divide-slate-200 text-sm">
                        {summary.disallowances.map((d, i) => (
                            <div key={i} className="px-8 py-5 hover:bg-slate-50/50 transition-colors">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="font-bold text-navy">{d.item}</span>
                                    <Badge variant="destructive" className="bg-red-50 text-red-600 border-red-100 text-[10px] font-bold uppercase tracking-widest">
                                        −₹{d.amount_cut.toFixed(2)} Cr
                                    </Badge>
                                </div>
                                <p className="text-[12px] text-muted-foreground leading-relaxed italic">"{d.justification}"</p>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            <div className="bg-white p-8 rounded-2xl border-2 border-slate-100 shadow-xl space-y-8">
                <div className="space-y-2">
                    <h4 className="text-lg font-bold text-navy tracking-tight">Final Decision</h4>
                    <p className="text-xs text-muted-foreground font-medium">Approve the AI audit findings as-is or provide specific regulatory overrides.</p>
                </div>

                <div className="flex flex-col md:flex-row gap-4">
                    <Button
                        onClick={() => onReviewSubmit(true)}
                        disabled={isSubmitting}
                        className="flex-1 bg-green-600 hover:bg-green-700 text-white rounded-xl h-16 font-bold text-lg gap-2 shadow-lg shadow-green-100"
                    >
                        {isSubmitting ? <Loader2 className="animate-spin" /> : <ThumbsUp size={20} />} Approve Findings
                    </Button>

                    <div className="flex-[2] flex gap-2">
                        <input
                            className="flex-1 rounded-xl border-slate-200 bg-slate-50 px-6 text-sm font-medium focus:ring-navy focus:border-navy transition-all"
                            placeholder="Enter specific override instruction (e.g., 'Allow Rs 10L for...')"
                            value={overrideText}
                            onChange={(e) => setOverrideText(e.target.value)}
                        />
                        <Button
                            variant="outline"
                            disabled={!overrideText.trim() || isSubmitting}
                            onClick={() => onReviewSubmit(false, overrideText)}
                            className="rounded-xl border-navy text-navy h-16 px-6 font-bold hover:bg-navy hover:text-white transition-all gap-2"
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
        green: 'text-green-600',
        blue: 'text-blue-600',
        red: 'text-red-600',
        none: 'text-navy'
    };
    return (
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground mb-2">{label}</p>
            <div className="flex items-baseline gap-1.5">
                <span className={`text-xl font-bold tracking-tight ${colorMap[highlight || 'none']}`}>₹{value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                <span className="text-[10px] font-bold text-muted-foreground">Cr</span>
            </div>
        </div>
    );
}
