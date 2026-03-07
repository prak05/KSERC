"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Info, FileText, FileSpreadsheet, Folder, Zap, Play, ChevronRight, CheckCircle2, Loader2, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { motion, AnimatePresence } from "framer-motion";

type Step = 'dashboard' | 'setup' | 'upload' | 'analysis';

export default function DashboardClient() {
    const router = useRouter();

    const [currentStep, setCurrentStep] = useState<Step>('dashboard');
    const [licensee, setLicensee] = useState<string>("");
    const [otherLicensee, setOtherLicensee] = useState("");
    const [fy, setFy] = useState("2024-25");
    const [aicpi, setAicpi] = useState("4.2");
    const [files, setFiles] = useState<(File | null)[]>([null, null, null, null]);

    // Analysis state
    const [isUploading, setIsUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [statusText, setStatusText] = useState("");
    const [log, setLog] = useState<string[]>([]);

    const [recentCases, setRecentCases] = useState<any[]>([]);
    const [loadingCases, setLoadingCases] = useState(true);

    useEffect(() => {
        fetchCases();
    }, []);

    const fetchCases = async () => {
        setLoadingCases(true);
        try {
            const res = await fetch('/api/get-results?caseId=all');
            const data = await res.json();
            if (data.cases) {
                setRecentCases(data.cases.map((c: any) => ({
                    id: c.id,
                    licensee: c.licensees?.name || 'Unknown',
                    fy: c.financial_year,
                    status: c.status,
                    state: c.revenue_gap_cr > 0 ? 'gap' : 'surplus',
                    gap: Math.abs(c.revenue_gap_cr || 0).toFixed(2)
                })));
            }
        } catch (e) {
            console.error("Error fetching cases", e);
        } finally {
            setLoadingCases(false);
        }
    };

    const handleDeleteCase = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (confirm("Are you sure you want to delete this analysis?")) {
            try {
                const res = await fetch(`/api/delete-case?caseId=${id}`, { method: 'DELETE' });
                if (res.ok) fetchCases();
            } catch (err) {
                console.error("Error deleting case", err);
            }
        }
    };

    const uploadCount = files.filter(Boolean).length;
    const canRun = files[0] && files[1] && licensee;

    const addLog = (msg: string) => {
        setLog(prev => [...prev, `> ${msg}`]);
    };

    const handleFileChange = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const newFiles = [...files];
            newFiles[index] = e.target.files[0];
            setFiles(newFiles);
        }
    };

    const runAnalysis = async () => {
        try {
            setCurrentStep('analysis');
            setIsUploading(true);
            setLog([]);
            setProgress(5);
            const activeLicensee = licensee === "Other" ? otherLicensee : licensee;
            setStatusText("Initializing analysis...");
            addLog(`Session: ${activeLicensee} · FY ${fy}`);

            // Upload documents to API
            setProgress(20);
            setStatusText("Uploading and parsing documents...");

            const formData = new FormData();
            formData.append("licensee", activeLicensee);
            formData.append("fy", fy);
            files.forEach((f) => {
                if (f) formData.append("file", f);
            });

            addLog("Extracting text and structured data via LLM...");
            const extractRes = await fetch("/api/extract", {
                method: "POST",
                body: formData,
            });

            const extractData = await extractRes.json();
            if (!extractRes.ok) throw new Error(extractData.error);

            setProgress(60);
            setStatusText("Extraction complete. Running analysis...");
            addLog("Data successfully structured. Running KSERC rules engine...");

            // Initialize case via Local DB API
            const initRes = await fetch("/api/init-case", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ fy, activeLicensee, extractData })
            });
            const initData = await initRes.json();
            if (!initRes.ok) throw new Error(initData.error || "Failed to initialize case");
            const caseRecordId = initData.caseId;

            // Run Analysis Endpoint
            setProgress(80);
            setStatusText("Generating Prudence Checks & AI Veridcts...");
            addLog("Consulting knowledge base and computing deviations...");

            const analyseRes = await fetch("/api/analyse", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ caseId: caseRecordId, aicpi: parseFloat(aicpi), licenseeName: activeLicensee })
            });

            const analyseData = await analyseRes.json();
            if (!analyseRes.ok) throw new Error(analyseData.error);

            setProgress(100);
            setStatusText("Complete.");
            addLog("Analysis pipeline finished successfully.");

            setTimeout(() => {
                router.push(`/results?caseId=${caseRecordId}`);
            }, 1000);

        } catch (e: unknown) {
            console.error(e);
            setStatusText("Analysis Failed");
            const msg = e instanceof Error ? e.message : (typeof e === 'object' ? JSON.stringify(e) : String(e));
            addLog(`ERROR: ${msg}`);
            setProgress(100);
        }
    };

    const variants: any = {
        initial: { opacity: 0, y: 15, scale: 0.98 },
        animate: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
        exit: { opacity: 0, scale: 0.96, transition: { duration: 0.2 } },
    };

    return (
        <div className="mx-auto max-w-5xl space-y-6 pt-4 pb-12">
            {/* Header */}
            <header className="flex items-center justify-between pb-4 border-b">
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 flex items-center justify-center rounded-lg bg-navy text-white font-bold font-serif text-xl shadow-md">K</div>
                    <div>
                        <h1 className="text-xl font-bold text-navy tracking-tight leading-none">AI Truing-Up Tool</h1>
                        <p className="text-xs text-muted-foreground uppercase tracking-widest mt-1">KSERC Internal System</p>
                    </div>
                </div>
                {currentStep !== 'dashboard' && currentStep !== 'analysis' && (
                    <Button variant="ghost" size="sm" onClick={() => setCurrentStep('dashboard')} className="text-muted-foreground">
                        <ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard
                    </Button>
                )}
            </header>

            <AnimatePresence mode="wait">
                {/* STEP 1: DASHBOARD */}
                {currentStep === 'dashboard' && (
                    <motion.div key="dashboard" variants={variants} initial="initial" animate="animate" exit="exit" className="space-y-8">
                        <div>
                            <h2 className="text-3xl font-bold tracking-tight text-navy mb-2">Dashboard</h2>
                            <p className="text-muted-foreground">Overview of recent filings and analysis statuses.</p>
                        </div>

                        {/* Summary Cards */}
                        <div className="grid md:grid-cols-3 grid-cols-1 gap-4">
                            {loadingCases ? (
                                <div className="col-span-3 py-12 text-center text-muted-foreground animate-pulse text-sm">
                                    Loading saved analyses from Local DB...
                                </div>
                            ) : recentCases.length === 0 ? (
                                <div className="col-span-3 py-12 text-center text-muted-foreground bg-slate-50 border border-dashed rounded-xl">
                                    No saved analyses found. Start a new one below!
                                </div>
                            ) : (
                                recentCases.map((rc, i) => (
                                    <motion.div key={i} whileHover={{ y: -4, boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)' }} className="transition-all duration-300">
                                        <Card className={`overflow-hidden border-t-4 ${rc.state === 'gap' ? 'border-t-red-500' : 'border-t-blue'} shadow-sm`}>
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-[15px] truncate">{rc.licensee}</CardTitle>
                                                <CardDescription className="text-xs">FY {rc.fy}</CardDescription>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                                                    {rc.state === 'gap' ? 'Gap' : 'Surplus'}
                                                </div>
                                                <div className={`text-2xl font-mono font-bold ${rc.state === 'gap' ? 'text-red-600' : 'text-navy'}`}>
                                                    {rc.gap !== 'Pending' ? `₹${rc.gap} Cr` : 'Pending'}
                                                </div>
                                                <div className="flex justify-between items-center mt-3">
                                                    <Badge variant="outline" className="bg-slate-50">{rc.status}</Badge>
                                                    <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-700 hover:bg-red-50 p-1 h-auto" onClick={(e) => handleDeleteCase(rc.id, e)}>Delete</Button>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </motion.div>
                                ))
                            )}
                        </div>

                        {/* Recent Activity List */}
                        <Card className="shadow-sm">
                            <CardHeader className="bg-slate-50/50 border-b">
                                <CardTitle className="text-[15px]">Recent Activity</CardTitle>
                            </CardHeader>
                            <CardContent className="p-0">
                                <div className="divide-y text-sm">
                                    {recentCases.slice(0, 5).map((rc, i) => (
                                        <div key={i} className="flex items-center justify-between p-4 hover:bg-slate-50/80 transition-colors cursor-pointer" onClick={() => router.push(`/results?caseId=${rc.id}`)}>
                                            <div className="flex items-center gap-3">
                                                <div className={`w-2 h-2 rounded-full ${rc.state === 'gap' ? 'bg-red-500' : 'bg-blue'}`}></div>
                                                <span className="font-medium text-navy">{rc.licensee}</span>
                                                <span className="text-muted-foreground">FY {rc.fy} &mdash; {rc.status}</span>
                                            </div>
                                            <Button variant="ghost" size="sm" className="h-8 text-blue"><ChevronRight size={16} /></Button>
                                        </div>
                                    ))}
                                    {!loadingCases && recentCases.length === 0 && (
                                        <div className="p-4 text-muted-foreground text-center">No recent activity.</div>
                                    )}
                                </div>
                            </CardContent>
                        </Card>

                        <div className="flex justify-center pt-4">
                            <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                                <Button size="lg" onClick={() => setCurrentStep('setup')} className="bg-blue hover:bg-blue-light text-base h-12 px-8 shadow-md">
                                    + Start New Truing-Up Analysis
                                </Button>
                            </motion.div>
                        </div>
                    </motion.div>
                )}

                {/* STEP 2: SETUP (Select Licensee & Year) */}
                {currentStep === 'setup' && (
                    <motion.div key="setup" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-2xl mx-auto space-y-6">
                        <div className="mb-8">
                            <div className="flex items-center gap-2 text-sm text-blue mb-4 font-medium tracking-wide">
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue text-white text-xs">1</span>
                                <span>Step 1 of 3: Select Licensee & Year</span>
                            </div>
                            <h2 className="text-3xl font-bold tracking-tight text-navy mb-2">Analysis Parameters</h2>
                            <p className="text-muted-foreground">Select the distribution licensee and the financial year for the truing-up process.</p>
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
                                            <SelectItem value="Infoparks">Infoparks Kerala</SelectItem>
                                            <SelectItem value="Technopark">Electronics Technology Parks – Kerala (Technopark)</SelectItem>
                                            <SelectItem value="KDHP">Kanan Devan Hills Plantations Company (KDHP)</SelectItem>
                                            <SelectItem value="CSEZA">Cochin Special Economic Zone Authority (CSEZA)</SelectItem>
                                            <SelectItem value="Other">Other (specify below)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                {licensee === "Other" && (
                                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-2.5">
                                        <Label className="text-xs uppercase tracking-wider text-muted-foreground">Licensee Name (Custom)</Label>
                                        <Input
                                            className="h-12 text-base"
                                            placeholder="Enter full licensee name..."
                                            value={otherLicensee}
                                            onChange={(e) => setOtherLicensee(e.target.value)}
                                        />
                                    </motion.div>
                                )}

                                <div className="grid grid-cols-2 gap-4 pt-2">
                                    <div className="space-y-2.5">
                                        <Label className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Financial Year</Label>
                                        <Select value={fy} onValueChange={setFy}>
                                            <SelectTrigger className="h-12">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="2024-25">2024-25</SelectItem>
                                                <SelectItem value="2023-24">2023-24</SelectItem>
                                                <SelectItem value="2022-23">2022-23</SelectItem>
                                                <SelectItem value="2021-22">2021-22</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2.5">
                                        <Label className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">AICPI Rate (%)</Label>
                                        <Input className="h-12" type="number" step="0.1" value={aicpi} onChange={(e) => setAicpi(e.target.value)} />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <div className="flex justify-end pt-4">
                            <Button
                                size="lg"
                                disabled={!licensee || (licensee === 'Other' && !otherLicensee)}
                                onClick={() => setCurrentStep('upload')}
                                className="bg-navy hover:bg-navy-dark px-8"
                            >
                                Next Step <ChevronRight className="ml-2 h-4 w-4" />
                            </Button>
                        </div>
                    </motion.div>
                )}

                {/* STEP 3: UPLOAD */}
                {currentStep === 'upload' && (
                    <motion.div key="upload" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-4xl mx-auto space-y-6">
                        <div className="mb-8">
                            <div className="flex items-center gap-2 text-sm text-blue mb-4 font-medium tracking-wide">
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue text-white text-xs">2</span>
                                <span>Step 2 of 3: Upload Required Documents</span>
                                <span className="mx-2 text-muted-foreground">/</span>
                                <span className="text-muted-foreground flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-green-500" /> {licensee === "Other" ? otherLicensee : licensee} (FY {fy})</span>
                            </div>
                            <h2 className="text-3xl font-bold tracking-tight text-navy mb-2">Document Ingestion</h2>
                            <p className="text-muted-foreground">Providing the correct documents ensures accurate LLM data extraction for prudence checks.</p>
                        </div>

                        <div className="mb-6 flex items-start gap-3 rounded-lg border border-blue/20 bg-blue/5 p-4 text-[13.5px] text-blue-900 shadow-sm">
                            <Info className="mt-0.5 shrink-0 text-blue" size={18} />
                            <div className="leading-relaxed">
                                <b>How this works:</b> Upload your documents below. The AI reads them, extracts financial figures, applies all KSERC regulatory formulas, and computes the Revenue Gap or Surplus from the actual data.
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            {[
                                { label: "Annual Accounts (Audited)", req: true, icon: FileText, types: ".pdf,.xlsx", desc: "Balance Sheet & P&L" },
                                { label: "ARR Order", req: true, icon: FileSpreadsheet, types: ".pdf,.xlsx", desc: "Commission-approved baseline" },
                                { label: "Previous Truing-Up Order", req: false, icon: Folder, types: ".pdf", desc: "For historical context" },
                                { label: "Tariff Schedule / Energy Audit", req: false, icon: Zap, types: ".pdf,.xlsx", desc: "For AT&C computation" }
                            ].map((box, i) => (
                                <motion.div key={i} whileHover={{ scale: 1.01 }} className="space-y-2">
                                    <div className="text-xs font-bold uppercase tracking-wide text-navy flex items-center justify-between px-1">
                                        <span>{box.label}</span>
                                        {box.req ? <span className="text-red-500 text-[10px]">*Required</span> : <span className="text-muted-foreground text-[10px] font-normal tracking-normal">(Optional)</span>}
                                    </div>
                                    <Label
                                        htmlFor={`file-${i}`}
                                        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 text-center transition-all duration-200 
                                            ${files[i]
                                                ? "border-green-500 bg-green-50/40 border-solid shadow-[0_0_15px_rgba(34,197,94,0.1)]"
                                                : "border-slate-300 hover:border-blue/50 hover:bg-slate-50"
                                            }`}
                                    >
                                        <box.icon className={`mb-3 h-8 w-8 transition-colors ${files[i] ? "text-green-600" : "text-slate-400"}`} />
                                        <div className="text-sm font-semibold text-slate-800 mb-1">
                                            {files[i] ? files[i]?.name : "Click to upload file"}
                                        </div>
                                        <div className="text-xs text-slate-500">
                                            {files[i] ? `${(files[i]!.size / 1024 / 1024).toFixed(2)} MB · Ready to parse` : box.desc}
                                        </div>
                                        <input
                                            type="file"
                                            id={`file-${i}`}
                                            className="hidden"
                                            accept={box.types}
                                            onChange={(e) => handleFileChange(i, e)}
                                        />
                                    </Label>
                                </motion.div>
                            ))}
                        </div>

                        <div className="flex justify-between items-center pt-8 border-t mt-8">
                            <Button variant="outline" onClick={() => setCurrentStep('setup')}>Back</Button>
                            <Button
                                size="lg"
                                disabled={!canRun}
                                onClick={runAnalysis}
                                className="bg-blue hover:bg-blue-light text-base px-8 shadow-md gap-2 shadow-blue/20"
                            >
                                Run AI Analysis <Play size={16} fill="currentColor" />
                            </Button>
                        </div>
                    </motion.div>
                )}

                {/* STEP 4: AI ANALYSIS (3D Console) */}
                {currentStep === 'analysis' && (
                    <motion.div key="analysis" variants={variants} initial="initial" animate="animate" exit="exit" className="max-w-3xl mx-auto">
                        <div className="mb-6 flex flex-col items-center justify-center text-center">
                            <div className="relative mb-6">
                                <div className="absolute inset-0 rounded-full animate-ping opacity-20 bg-blue"></div>
                                <div className="h-16 w-16 rounded-full bg-navy flex items-center justify-center shadow-lg shadow-navy/30 relative z-10">
                                    {statusText === "Analysis Failed" ? (
                                        <span className="text-red-500 text-2xl font-bold">X</span>
                                    ) : (
                                        <Loader2 className="h-8 w-8 text-cyan-400 animate-spin" />
                                    )}
                                </div>
                            </div>
                            <h2 className="text-2xl font-bold tracking-tight text-navy mb-2">
                                Analyzing: {licensee === "Other" ? otherLicensee : licensee} — FY {fy}
                            </h2>
                            <p className="text-muted-foreground">{statusText}</p>
                        </div>

                        {/* 3D Console Box */}
                        <div
                            className="relative overflow-hidden rounded-xl border border-slate-700 bg-[#0A1628] shadow-2xl transition-all"
                            style={{
                                transformStyle: 'preserve-3d',
                                transform: 'perspective(1000px) rotateX(2deg)',
                                boxShadow: '0 25px 50px -12px rgba(8, 20, 40, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05) inset'
                            }}
                        >
                            {/* Glass reflection top edge */}
                            <div className="absolute top-0 left-0 right-0 height-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>

                            <div className="flex items-center justify-between border-b border-slate-700/50 bg-[#0F1E35] px-4 py-2.5">
                                <div className="flex items-center gap-2">
                                    <div className="h-2.5 w-2.5 rounded-full bg-red-500/80"></div>
                                    <div className="h-2.5 w-2.5 rounded-full bg-amber-500/80"></div>
                                    <div className="h-2.5 w-2.5 rounded-full bg-green-500/80"></div>
                                </div>
                                <div className="text-[10px] uppercase tracking-widest text-slate-400 font-mono">
                                    KSERC Rules Engine v1.0
                                </div>
                                <div className="font-mono text-xs font-bold text-cyan-400">{progress}%</div>
                            </div>

                            {/* Progress bar line */}
                            <div className="h-1 w-full bg-[#0A1628]">
                                <motion.div
                                    className={`h-full ${statusText === "Analysis Failed" ? 'bg-red-500' : 'bg-cyan-500'}`}
                                    initial={{ width: '0%' }}
                                    animate={{ width: `${progress}%` }}
                                    transition={{ duration: 0.5 }}
                                    style={{
                                        boxShadow: statusText !== "Analysis Failed" ? '0 0 10px rgba(6, 182, 212, 0.6)' : 'none'
                                    }}
                                />
                            </div>

                            <div className="h-64 overflow-y-auto p-5 font-mono text-[13px] leading-[1.8] text-emerald-400/80 space-y-1.5 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
                                <AnimatePresence initial={false}>
                                    {log.map((l, i) => (
                                        <motion.div
                                            key={i}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            className={l.includes('ERROR:') ? 'text-red-400 font-bold' : l.includes('Session:') ? 'text-blue-400' : ''}
                                        >
                                            <span className="opacity-50 text-slate-500 mr-2">{new Date().toISOString().substring(11, 19)}</span>
                                            {l}
                                        </motion.div>
                                    ))}
                                </AnimatePresence>
                                {!statusText.includes("Failed") && progress < 100 && (
                                    <motion.div
                                        animate={{ opacity: [0.4, 1, 0.4] }}
                                        transition={{ repeat: Infinity, duration: 1.5 }}
                                        className="text-cyan-400/50"
                                    >
                                        _ blinking cursor
                                    </motion.div>
                                )}
                            </div>
                        </div>

                        <div className="mt-8 text-center text-[11px] text-muted-foreground uppercase tracking-widest">
                            {statusText === "Analysis Failed"
                                ? "Analysis encountered a fatal error. Please review the logs."
                                : "Please do not close this window while AI extraction is running."}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
