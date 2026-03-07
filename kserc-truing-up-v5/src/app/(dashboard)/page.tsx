"use client";

import { useState, useEffect, useRef } from "react";
import { Info, FileText, Play, ChevronRight, CheckCircle2, Loader2, ArrowLeft, AlertTriangle, ThumbsUp, Edit3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { motion, AnimatePresence } from "framer-motion";

// ─── v5: now uses Python backend via /api/analyse → /api/status → /api/review ───

type Step = 'setup' | 'upload' | 'running' | 'review' | 'completed' | 'error';

interface Disallowance {
    item: string;
    claimed: number;
    approved: number;
    amount_cut: number;
    justification: string;
}

interface ReviewSummary {
    licensee: string;
    financial_year: string;
    total_claimed: number;
    total_approved: number;
    total_revenue: number;
    gap_surplus: number;
    disallowances: Disallowance[];
}

interface AnalysisResult {
    licensee_name: string;
    financial_year: string;
    total_claimed_expenditure: number;
    total_approved_expenditure: number;
    total_approved_revenue: number;
    final_revenue_gap_surplus: number;
    imputed_interest_on_surplus: number;
    human_override_notes: string | null;
    output_pdf_path: string;
    claimed_expenses: Record<string, number>;
    approved_expenses: Record<string, number>;
    disallowance_log: Disallowance[];
    error?: string;
}

const LICENSEES = ["Technopark", "Infopark", "CSEZA", "KDHP"];
const FINANCIAL_YEARS = ["2024-25", "2023-24", "2022-23", "2021-22", "2020-21"];

const variants: any = {
    initial: { opacity: 0, y: 15, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
    exit: { opacity: 0, scale: 0.96, transition: { duration: 0.2 } },
};

export default function DashboardClientV5() {
    const [step, setStep] = useState<Step>('setup');
    const [licensee, setLicensee] = useState("");
    const [fy, setFy] = useState("2023-24");
    const [pdfFile, setPdfFile] = useState<File | null>(null);

    // Analysis tracking
    const [analysisId, setAnalysisId] = useState<string | null>(null);
    const [log, setLog] = useState<string[]>([]);
    const [statusText, setStatusText] = useState("");
    const [progress, setProgress] = useState(0);
    const pollRef = useRef<NodeJS.Timeout | null>(null);

    // HITL review
    const [reviewSummary, setReviewSummary] = useState<ReviewSummary | null>(null);
    const [overrideText, setOverrideText] = useState("");
    const [isSubmittingReview, setIsSubmittingReview] = useState(false);

    // Final results
    const [result, setResult] = useState<AnalysisResult | null>(null);
    const [errorMsg, setErrorMsg] = useState("");

    const addLog = (msg: string) => setLog(prev => [...prev, msg]);

    // Cleanup poll on unmount
    useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

    // ── Step 1 → 2: Submit PDF to backend ─────────────────────────────
    const runAnalysis = async () => {
        if (!pdfFile || !licensee) return;
        setStep('running');
        setLog([]);
        setProgress(10);
        setStatusText("Uploading petition PDF to backend...");
        addLog(`▶  Starting pipeline: ${licensee} · FY ${fy}`);

        try {
            const formData = new FormData();
            formData.append("pdf", pdfFile);
            formData.append("licensee", licensee);
            formData.append("financial_year", fy);

            const res = await fetch("/api/analyse", { method: "POST", body: formData });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ error: "Upload failed" }));
                throw new Error(err.error || `HTTP ${res.status}`);
            }
            const { analysis_id } = await res.json();
            setAnalysisId(analysis_id);
            addLog(`✓  Job started: ${analysis_id}`);
            setProgress(25);
            setStatusText("Running Gemini Vision extraction...");
            startPolling(analysis_id);
        } catch (e: any) {
            setErrorMsg(e.message || "Failed to start analysis");
            setStep('error');
        }
    };

    // ── Poll /api/status/[id] every 3 seconds ────────────────────────
    const startPolling = (id: string) => {
        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${id}`, { cache: "no-store" });
                if (!res.ok) return;
                const data = await res.json();

                if (data.status === "RUNNING") {
                    setProgress(prev => Math.min(prev + 5, 80));
                    if (progress < 40) setStatusText("Extracting ARR data with Gemini Vision...");
                    else if (progress < 60) setStatusText("Running KSERC compliance audit...");
                    else setStatusText("Finalizing audit results...");
                    addLog(`…  Pipeline running (stage ${Math.round(progress / 20)})`);
                } else if (data.status === "AWAITING_REVIEW") {
                    if (pollRef.current) clearInterval(pollRef.current);
                    setReviewSummary(data.review_summary);
                    setProgress(90);
                    setStep('review');
                    addLog("⏸  Human review required — pipeline paused at HITL gate");
                } else if (data.status === "COMPLETED") {
                    if (pollRef.current) clearInterval(pollRef.current);
                    setResult(data.result);
                    setProgress(100);
                    setStep('completed');
                    addLog("✓  Pipeline complete!");
                } else if (data.status === "FAILED") {
                    if (pollRef.current) clearInterval(pollRef.current);
                    setErrorMsg(data.result?.error || "Pipeline failed");
                    setStep('error');
                    addLog(`✗  Pipeline failed: ${data.result?.error}`);
                }
            } catch {
                // Transient network error — keep polling
            }
        }, 3000);
    };

    // ── Submit HITL review ────────────────────────────────────────────
    const submitReview = async (approve: boolean) => {
        if (!analysisId) return;
        setIsSubmittingReview(true);
        const response = approve ? "Approve" : overrideText.trim();
        if (!response) { setIsSubmittingReview(false); return; }

        try {
            const res = await fetch("/api/review", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ analysis_id: analysisId, response }),
            });
            if (!res.ok) throw new Error("Review submission failed");
            addLog(`✓  Review submitted: "${response}"`);
            setStep('running');
            setStatusText("Generating PDF order...");
            setProgress(92);
            startPolling(analysisId);
        } catch (e: any) {
            setErrorMsg(e.message);
            setStep('error');
        } finally {
            setIsSubmittingReview(false);
        }
    };

    const gapOrSurplus = result
        ? result.final_revenue_gap_surplus >= 0 ? "Surplus" : "Gap"
        : "";
    const absGapSurplus = result ? Math.abs(result.final_revenue_gap_surplus) : 0;

    return (
        <div className="mx-auto max-w-5xl space-y-6 pt-4 pb-16">
            {/* ── Header ─────────────────────────────────────────────── */}
            <header className="flex items-center justify-between pb-4 border-b">
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-navy text-white font-bold font-serif text-xl shadow-md">K</div>
                    <div>
                        <h1 className="text-xl font-bold text-navy tracking-tight leading-none">AI Truing-Up Tool <span className="ml-1 text-xs text-blue bg-blue/10 px-2 py-0.5 rounded-full font-mono">v5</span></h1>
                        <p className="text-xs text-muted-foreground uppercase tracking-widest mt-1">KSERC Internal System · Python Backend</p>
                    </div>
                </div>
                {(step === 'upload' || step === 'review') && (
                    <Button variant="ghost" size="sm" onClick={() => { setStep('setup'); setPdfFile(null); }} className="text-muted-foreground">
                        <ArrowLeft className="mr-2 h-4 w-4" /> Back
                    </Button>
                )}
            </header>

            <AnimatePresence mode="wait">

                {/* ── STEP 1: SETUP ────────────────────────────────── */}
                {step === 'setup' && (
                    <motion.div key="setup" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-2xl mx-auto space-y-6">
                        <div>
                            <div className="flex items-center gap-2 text-sm text-blue mb-4 font-medium">
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue text-white text-xs">1</span>
                                <span>Step 1 of 2: Select Licensee &amp; Year</span>
                            </div>
                            <h2 className="text-3xl font-bold tracking-tight text-navy mb-2">Analysis Parameters</h2>
                            <p className="text-muted-foreground">Select the distribution licensee and the financial year for truing-up.</p>
                        </div>
                        <Card className="shadow-md border-blue/20">
                            <CardContent className="p-6 space-y-6">
                                <div className="space-y-2.5">
                                    <Label className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Distribution Licensee</Label>
                                    <Select value={licensee} onValueChange={setLicensee}>
                                        <SelectTrigger className="h-12 text-base">
                                            <SelectValue placeholder="— Select licensee —" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {LICENSEES.map(l => (
                                                <SelectItem key={l} value={l}>{l}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2.5">
                                    <Label className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Financial Year</Label>
                                    <Select value={fy} onValueChange={setFy}>
                                        <SelectTrigger className="h-12">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {FINANCIAL_YEARS.map(y => (
                                                <SelectItem key={y} value={y}>{y}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </CardContent>
                        </Card>
                        <div className="flex justify-end pt-2">
                            <Button size="lg" disabled={!licensee} onClick={() => setStep('upload')} className="bg-navy hover:bg-navy/90 px-8">
                                Next <ChevronRight className="ml-2 h-4 w-4" />
                            </Button>
                        </div>
                    </motion.div>
                )}

                {/* ── STEP 2: UPLOAD ───────────────────────────────── */}
                {step === 'upload' && (
                    <motion.div key="upload" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-2xl mx-auto space-y-6">
                        <div>
                            <div className="flex items-center gap-2 text-sm text-blue mb-4 font-medium">
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue text-white text-xs">2</span>
                                <span>Step 2 of 2: Upload Petition PDF</span>
                                <span className="text-muted-foreground">/ {licensee} · FY {fy}</span>
                            </div>
                            <h2 className="text-3xl font-bold tracking-tight text-navy mb-2">Document Upload</h2>
                            <p className="text-muted-foreground">Upload the KSERC truing-up petition PDF. Gemini Vision will extract the ARR table automatically.</p>
                        </div>

                        <div className="flex items-start gap-3 rounded-lg border border-blue/20 bg-blue/5 p-4 text-[13.5px] text-blue-900">
                            <Info className="mt-0.5 shrink-0 text-blue" size={18} />
                            <div><b>What happens next:</b> Gemini Vision reads the petition, the KSERC compliance auditor runs all regulatory formulas (two-way PPC, Reg 27 depreciation, RoNFA, SBI rates), then pauses for your review before drafting the PDF order.</div>
                        </div>

                        <Label
                            htmlFor="petition-pdf"
                            className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 text-center transition-all duration-200
                                ${pdfFile ? "border-green-500 bg-green-50/40 border-solid" : "border-slate-300 hover:border-blue/50 hover:bg-slate-50"}`}
                        >
                            <FileText className={`mb-3 h-10 w-10 ${pdfFile ? "text-green-600" : "text-slate-400"}`} />
                            <div className="text-sm font-semibold text-slate-800 mb-1">
                                {pdfFile ? pdfFile.name : "Click to upload petition PDF"}
                            </div>
                            <div className="text-xs text-slate-500">
                                {pdfFile ? `${(pdfFile.size / 1024 / 1024).toFixed(2)} MB · Ready` : "Accepts .pdf files only"}
                            </div>
                            <input type="file" id="petition-pdf" accept=".pdf" className="hidden"
                                onChange={e => { if (e.target.files?.[0]) setPdfFile(e.target.files[0]); }} />
                        </Label>

                        <div className="flex justify-between items-center pt-4 border-t">
                            <Button variant="outline" onClick={() => setStep('setup')}>Back</Button>
                            <Button size="lg" disabled={!pdfFile} onClick={runAnalysis}
                                className="bg-blue hover:bg-blue/90 text-base px-8 shadow-md gap-2">
                                Run AI Analysis <Play size={16} fill="currentColor" />
                            </Button>
                        </div>
                    </motion.div>
                )}

                {/* ── STEP 3: RUNNING ──────────────────────────────── */}
                {step === 'running' && (
                    <motion.div key="running" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-3xl mx-auto">
                        <div className="mb-6 flex flex-col items-center justify-center text-center">
                            <div className="relative mb-6">
                                <div className="absolute inset-0 rounded-full animate-ping opacity-20 bg-blue"></div>
                                <div className="h-16 w-16 rounded-full bg-navy flex items-center justify-center shadow-lg shadow-navy/30 relative z-10">
                                    <Loader2 className="h-8 w-8 text-cyan-400 animate-spin" />
                                </div>
                            </div>
                            <h2 className="text-2xl font-bold tracking-tight text-navy mb-1">Analysing: {licensee} — FY {fy}</h2>
                            <p className="text-muted-foreground text-sm">{statusText}</p>
                        </div>

                        <div className="relative overflow-hidden rounded-xl border border-slate-700 bg-[#0A1628] shadow-2xl"
                            style={{ transform: 'perspective(1000px) rotateX(2deg)', boxShadow: '0 25px 50px -12px rgba(8,20,40,0.5)' }}>
                            <div className="flex items-center justify-between border-b border-slate-700/50 bg-[#0F1E35] px-4 py-2.5">
                                <div className="flex items-center gap-2">
                                    <div className="h-2.5 w-2.5 rounded-full bg-red-500/80"></div>
                                    <div className="h-2.5 w-2.5 rounded-full bg-amber-500/80"></div>
                                    <div className="h-2.5 w-2.5 rounded-full bg-green-500/80"></div>
                                </div>
                                <div className="text-[10px] uppercase tracking-widest text-slate-400 font-mono">KSERC Rules Engine v5</div>
                                <div className="font-mono text-xs font-bold text-cyan-400">{progress}%</div>
                            </div>
                            <div className="h-1 w-full bg-[#0A1628]">
                                <motion.div className="h-full bg-cyan-500" initial={{ width: '0%' }} animate={{ width: `${progress}%` }} transition={{ duration: 0.6 }}
                                    style={{ boxShadow: '0 0 10px rgba(6,182,212,0.6)' }} />
                            </div>
                            <div className="h-64 overflow-y-auto p-5 font-mono text-[13px] leading-[1.8] text-emerald-400/80 space-y-1.5">
                                <AnimatePresence initial={false}>
                                    {log.map((l, i) => (
                                        <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                                            className={l.includes('✗') ? 'text-red-400' : l.includes('⏸') ? 'text-amber-400' : ''}>
                                            <span className="opacity-40 text-slate-500 mr-2">{new Date().toISOString().substring(11, 19)}</span>{l}
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                                <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 1.5 }}
                                    className="text-cyan-400/50">▌</motion.div>
                            </div>
                        </div>
                        <p className="mt-6 text-center text-[11px] text-muted-foreground uppercase tracking-widest">
                            Please keep this window open while the AI pipeline runs.
                        </p>
                    </motion.div>
                )}

                {/* ── STEP 4: HITL REVIEW GATE ─────────────────────── */}
                {step === 'review' && reviewSummary && (
                    <motion.div key="review" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-4xl mx-auto space-y-6">
                        <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl">
                            <AlertTriangle className="text-amber-600 shrink-0" size={22} />
                            <div>
                                <p className="font-semibold text-amber-900">Human-in-the-Loop Review Required</p>
                                <p className="text-sm text-amber-700 mt-0.5">The AI pipeline has paused. Review the audit summary below, then approve or provide an override instruction.</p>
                            </div>
                        </div>

                        {/* Summary header */}
                        <Card>
                            <CardHeader className="bg-slate-50 border-b pb-3">
                                <CardTitle className="text-base text-navy">Audit Summary — {reviewSummary.licensee} · FY {reviewSummary.financial_year}</CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0">
                                    {[
                                        { label: "Total Claimed", value: `₹${reviewSummary.total_claimed.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`, color: "text-slate-700" },
                                        { label: "Total Approved", value: `₹${reviewSummary.total_approved.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`, color: "text-green-700" },
                                        { label: "Total Revenue", value: `₹${reviewSummary.total_revenue.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`, color: "text-blue" },
                                        {
                                            label: reviewSummary.gap_surplus >= 0 ? "Surplus" : "Gap",
                                            value: `₹${Math.abs(reviewSummary.gap_surplus).toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`,
                                            color: reviewSummary.gap_surplus >= 0 ? "text-green-700" : "text-red-600"
                                        },
                                    ].map(({ label, value, color }) => (
                                        <div key={label} className="p-4">
                                            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{label}</p>
                                            <p className={`text-lg font-mono font-bold ${color}`}>{value}</p>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Disallowances */}
                        {reviewSummary.disallowances.length > 0 && (
                            <Card>
                                <CardHeader className="bg-slate-50 border-b pb-3">
                                    <CardTitle className="text-sm text-navy">Disallowances ({reviewSummary.disallowances.length})</CardTitle>
                                </CardHeader>
                                <div className="divide-y text-sm">
                                    {reviewSummary.disallowances.map((d, i) => (
                                        <div key={i} className="px-5 py-3">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-semibold text-navy">{d.item}</span>
                                                <Badge variant="destructive" className="text-xs">−₹{d.amount_cut.toFixed(2)} L</Badge>
                                            </div>
                                            <p className="text-muted-foreground text-xs leading-relaxed line-clamp-2">{d.justification}</p>
                                        </div>
                                    ))}
                                </div>
                            </Card>
                        )}

                        {/* Review actions */}
                        <Card className="border-blue/20 shadow-md">
                            <CardContent className="p-6 space-y-4">
                                <p className="font-semibold text-navy">Your Decision</p>
                                <div className="flex gap-3">
                                    <Button size="lg" className="flex-1 bg-green-600 hover:bg-green-700 gap-2" disabled={isSubmittingReview}
                                        onClick={() => submitReview(true)}>
                                        <ThumbsUp size={16} /> Approve &amp; Generate PDF Order
                                    </Button>
                                </div>
                                <div className="relative">
                                    <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
                                    <div className="relative flex justify-center text-xs"><span className="bg-white px-2 text-muted-foreground">or provide an override</span></div>
                                </div>
                                <div className="flex gap-2">
                                    <input
                                        className="flex-1 h-10 rounded-md border border-input px-3 text-sm"
                                        placeholder='e.g. "Allow Rs 56 Lakhs for new Technocity campus"'
                                        value={overrideText}
                                        onChange={e => setOverrideText(e.target.value)}
                                    />
                                    <Button variant="outline" className="gap-2 shrink-0" disabled={!overrideText.trim() || isSubmittingReview}
                                        onClick={() => submitReview(false)}>
                                        <Edit3 size={14} /> Apply Override
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                )}

                {/* ── STEP 5: COMPLETED ─────────────────────────────── */}
                {step === 'completed' && result && (
                    <motion.div key="completed" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-4xl mx-auto space-y-6">
                        <div className="flex items-center gap-3">
                            <CheckCircle2 className="text-green-500" size={28} />
                            <div>
                                <h2 className="text-2xl font-bold text-navy">Analysis Complete</h2>
                                <p className="text-muted-foreground text-sm">{result.licensee_name} · FY {result.financial_year}</p>
                            </div>
                        </div>

                        {/* Key figures */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {[
                                { label: "Total Claimed", value: `₹${result.total_claimed_expenditure.toFixed(2)} L`, sub: "Expenses", color: "text-slate-700" },
                                { label: "Total Approved", value: `₹${result.total_approved_expenditure.toFixed(2)} L`, sub: "After audit", color: "text-green-700" },
                                { label: "Total Revenue", value: `₹${result.total_approved_revenue.toFixed(2)} L`, sub: "Approved", color: "text-blue" },
                                {
                                    label: `Revenue ${gapOrSurplus}`,
                                    value: `₹${absGapSurplus.toFixed(2)} L`,
                                    sub: gapOrSurplus === "Surplus" ? "Over-recovery" : "Under-recovery",
                                    color: gapOrSurplus === "Surplus" ? "text-green-700" : "text-red-600"
                                },
                            ].map(({ label, value, sub, color }) => (
                                <Card key={label} className="shadow-sm">
                                    <CardContent className="p-4">
                                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{label}</p>
                                        <p className={`text-xl font-mono font-bold ${color}`}>{value}</p>
                                        <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>

                        {/* Disallowances table */}
                        {result.disallowance_log.length > 0 && (
                            <Card>
                                <CardHeader className="bg-slate-50 border-b pb-3">
                                    <CardTitle className="text-sm text-navy">Disallowances in Final Order ({result.disallowance_log.length})</CardTitle>
                                </CardHeader>
                                <div className="divide-y text-sm">
                                    {result.disallowance_log.map((d, i) => (
                                        <div key={i} className="px-5 py-3 hover:bg-slate-50 transition-colors">
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex-1">
                                                    <p className="font-semibold text-navy text-sm">{d.item}</p>
                                                    <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{d.justification}</p>
                                                </div>
                                                <div className="text-right shrink-0">
                                                    <p className="text-xs text-muted-foreground">Claimed: ₹{d.claimed.toFixed(2)} L</p>
                                                    <p className="text-xs text-green-700">Approved: ₹{d.approved.toFixed(2)} L</p>
                                                    <Badge variant="destructive" className="text-xs mt-1">Cut: ₹{d.amount_cut.toFixed(2)} L</Badge>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </Card>
                        )}

                        {result.human_override_notes && (
                            <div className="flex items-start gap-2 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-4">
                                <Edit3 size={14} className="mt-0.5 shrink-0" />
                                <span><b>Override applied:</b> {result.human_override_notes}</span>
                            </div>
                        )}

                        <div className="flex justify-between items-center pt-4 border-t">
                            <Button variant="outline" onClick={() => { setStep('setup'); setResult(null); setAnalysisId(null); setPdfFile(null); }}>
                                New Analysis
                            </Button>
                            {result.output_pdf_path && analysisId && (
                                <Button className="bg-navy hover:bg-navy/90 gap-2" asChild>
                                    <a href={`http://localhost:8000/download/${analysisId}`} target="_blank" rel="noopener noreferrer">
                                        <FileText size={16} /> Download PDF Order
                                    </a>
                                </Button>
                            )}
                        </div>
                    </motion.div>
                )}

                {/* ── ERROR STATE ──────────────────────────────────── */}
                {step === 'error' && (
                    <motion.div key="error" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-2xl mx-auto text-center py-16 space-y-4">
                        <div className="h-16 w-16 rounded-full bg-red-100 flex items-center justify-center mx-auto">
                            <AlertTriangle className="text-red-600" size={28} />
                        </div>
                        <h2 className="text-xl font-bold text-navy">Pipeline Error</h2>
                        <p className="text-muted-foreground text-sm bg-slate-50 border rounded-lg p-4 font-mono">{errorMsg}</p>
                        <Button variant="outline" onClick={() => { setStep('setup'); setErrorMsg(''); }}>Start Over</Button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
