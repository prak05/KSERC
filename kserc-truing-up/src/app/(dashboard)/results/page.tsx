"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, Send, CheckCircle2, AlertTriangle, XCircle, Info, FileText, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { motion, AnimatePresence } from "framer-motion";

interface CostHead {
    id: string;
    head_name: string;
    actual_cr: number;
    approved_cr: number;
    final_allowed_cr: number;
    final_verdict: string;
    flag_level: string | null;
    ai_reason: string;
    ai_order_reference: string;
}

function ResultsContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const caseId = searchParams.get("caseId");

    const [loading, setLoading] = useState(true);
    const [caseData, setCaseData] = useState<any>(null);
    const [costHeads, setCostHeads] = useState<CostHead[]>([]);
    const [revenue, setRevenue] = useState<any>(null);
    const [selectedItem, setSelectedItem] = useState<CostHead | null>(null);

    // Chat State
    const [chatMessages, setChatMessages] = useState<{ role: string, content: string }[]>([
        { role: 'assistant', content: 'Analysis complete. I am ready to answer any questions regarding the regulatory formulas applied or specific deductions. How can I help?' }
    ]);
    const [chatInput, setChatInput] = useState("");
    const [chatLoading, setChatLoading] = useState(false);

    // Save Analysis State
    const [isSavingCase, setIsSavingCase] = useState(false);

    // Modify Expense State
    const [isModifyModalOpen, setIsModifyModalOpen] = useState(false);
    const [modifyValue, setModifyValue] = useState("");
    const [modifyNote, setModifyNote] = useState("");
    const [modifyVerdict, setModifyVerdict] = useState("");
    const [isModifying, setIsModifying] = useState(false);

    useEffect(() => {
        if (caseId) {
            fetchReportData();
        }
    }, [caseId]);

    const fetchReportData = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/get-results?caseId=${caseId}`);
            if (!res.ok) throw new Error("Failed to fetch results");
            const data = await res.json();

            setCaseData(data.cData);
            setCostHeads(data.chData || []);
            setRevenue(data.revData);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleSendMessage = async () => {
        if (!chatInput.trim() || chatLoading) return;
        const newMessages = [...chatMessages, { role: 'user', content: chatInput }];
        setChatMessages(newMessages);
        setChatInput("");
        setChatLoading(true);

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ caseId, messages: newMessages })
            });
            const data = await res.json();
            if (data.reply) {
                setChatMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
            }
        } catch (e) {
            console.error("Chat error", e);
        } finally {
            setChatLoading(false);
        }
    };

    const handleUpdateStatus = async (newStatus: string) => {
        setIsSavingCase(true);
        try {
            const res = await fetch("/api/save-analysis", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ caseId, status: newStatus })
            });
            if (res.ok) {
                setCaseData((prev: any) => prev ? { ...prev, status: newStatus } : null);
            }
        } catch (e) {
            console.error("Update status error", e);
        } finally {
            setIsSavingCase(false);
        }
    };

    const handleModifyValue = async () => {
        if (!selectedItem || !modifyValue || !modifyNote) return;
        setIsModifying(true);
        try {
            const res = await fetch("/api/update-cost-head", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    costHeadId: selectedItem.id,
                    newValue: parseFloat(modifyValue),
                    note: modifyNote,
                    newVerdict: modifyVerdict
                })
            });
            if (res.ok) {
                // Update local state without full refetch
                const updatedHeads = costHeads.map(h => {
                    if (h.id === selectedItem.id) {
                        return {
                            ...h,
                            final_allowed_cr: parseFloat(modifyValue),
                            final_verdict: modifyVerdict,
                            ai_reason: `[ADMIN OVERRIDE] ${modifyNote}\n\nOriginal AI Reason: ${h.ai_reason}`
                        };
                    }
                    return h;
                });
                setCostHeads(updatedHeads);
                setSelectedItem({
                    ...selectedItem,
                    final_allowed_cr: parseFloat(modifyValue),
                    final_verdict: modifyVerdict,
                    ai_reason: `[ADMIN OVERRIDE] ${modifyNote}\n\nOriginal AI Reason: ${selectedItem.ai_reason}`
                });
                setIsModifyModalOpen(false);
                setModifyValue("");
                setModifyNote("");
                setModifyVerdict("");
            }
        } catch (e) {
            console.error(e);
        } finally {
            setIsModifying(false);
        }
    };

    if (loading) {
        return (
            <div className="flex h-[60vh] items-center justify-center flex-col gap-4">
                <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-cyan-500 animate-spin"></div>
                <div className="text-navy font-medium animate-pulse">Loading Analysis Results...</div>
            </div>
        );
    }

    if (!caseData) {
        return (
            <div className="flex justify-center p-12">
                <Card className="w-full max-w-md p-8 text-center shadow-lg border-red-200">
                    <XCircle className="mx-auto h-12 w-12 text-red-500 mb-4" />
                    <h2 className="text-xl font-bold text-navy mb-2">Analysis Not Found</h2>
                    <p className="text-muted-foreground mb-6">Could not locate the requested Truing-Up session.</p>
                    <Button onClick={() => router.push("/")} className="bg-navy">Return Home</Button>
                </Card>
            </div>
        );
    }

    const totalClaimed = costHeads.reduce((s, h) => s + Number(h.actual_cr), 0);
    const totalApproved = costHeads.reduce((s, h) => s + Number(h.final_allowed_cr), 0);
    const totalDisallowed = totalClaimed - totalApproved;
    const gap = caseData.revenue_gap_cr;

    const isGap = gap > 0;

    const containerVariants = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const itemVariants: any = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
    };

    return (
        <motion.div variants={containerVariants} initial="hidden" animate="show" className="mx-auto max-w-6xl space-y-6 pt-4 pb-12">
            {/* Header / Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground font-medium tracking-wide">
                <button onClick={() => router.push("/")} className="transition-colors hover:text-blue">Dashboard</button>
                <ChevronRight className="h-3.5 w-3.5" />
                <span className="text-navy font-semibold">Analysis Results</span>
            </div>

            <div className="flex flex-wrap items-end justify-between gap-4 border-b pb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-navy mb-1 leading-none">
                        Truing-Up Results
                    </h1>
                    <div className="flex items-center gap-2 mt-2">
                        <span className="text-[14px] text-muted-foreground font-medium">
                            {caseData.licensees.name}
                        </span>
                        <Badge variant="outline" className="bg-slate-50 text-slate-600 font-mono text-[10px] tracking-widest">
                            FY {caseData.financial_year}
                        </Badge>
                    </div>
                </div>
                <div className="flex items-center gap-2.5">
                    <Select
                        value={caseData.status}
                        onValueChange={handleUpdateStatus}
                        disabled={isSavingCase}
                    >
                        <SelectTrigger className={`h-8 min-w-[140px] text-[10px] uppercase font-bold tracking-wider ${caseData.status === 'SAVED'
                            ? 'border-green-200 bg-green-50 text-green-800'
                            : 'border-amber-200 bg-amber-50 text-amber-800'
                            }`}>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="PARTIAL" className="text-[11px] uppercase tracking-wide">Partial Stage</SelectItem>
                            <SelectItem value="analysis_done" className="text-[11px] uppercase tracking-wide">AI Drafted</SelectItem>
                            <SelectItem value="SAVED" className="text-[11px] uppercase tracking-wide font-bold text-green-700">Approved</SelectItem>
                        </SelectContent>
                    </Select>
                    <Button variant="outline" onClick={() => router.push("/")} className="text-blue border-blue/20 hover:bg-blue-50 shadow-sm">
                        <ArrowLeft className="mr-2 h-4 w-4" /> Start Over
                    </Button>
                    <Button
                        onClick={() => handleUpdateStatus('SAVED')}
                        disabled={isSavingCase || caseData.status === 'SAVED'}
                        className="bg-green-600 hover:bg-green-700 shadow-md shadow-green-200"
                    >
                        <Save className="mr-2 h-4 w-4" />
                        {isSavingCase ? "Saving..." : "Save Analysis"}
                    </Button>
                    <Button onClick={() => router.push(`/report?caseId=${caseId}`)} className="bg-navy hover:bg-navy-dark shadow-md shadow-navy/20">
                        <FileText className="mr-2 h-4 w-4" /> Generate Order Draft
                    </Button>
                </div>
            </div>

            {/* Top Stat Cards - 3D Effect */}
            <div className="grid grid-cols-4 gap-4">
                {[
                    {
                        title: "Revenue Gap / Surplus",
                        value: `₹${Math.abs(gap).toFixed(2)} Cr`,
                        sub: isGap ? 'UNDER-RECOVERY (GAP)' : 'OVER-RECOVERY (SURPLUS)',
                        color: isGap ? 'border-t-red-500' : 'border-t-green-500',
                        textColor: isGap ? 'text-red-600' : 'text-green-600',
                        bg: 'bg-white'
                    },
                    {
                        title: "Claimed by Licensee",
                        value: `₹${totalClaimed.toFixed(2)} Cr`,
                        sub: 'FROM AUDITED ACCOUNTS',
                        color: 'border-t-amber-500',
                        textColor: 'text-amber-600',
                        bg: 'bg-white'
                    },
                    {
                        title: "AT&C Loss Computed",
                        value: `${revenue?.distribution_loss_pct || 0}%`,
                        sub: 'DISTRIBUTION EFFICIENCY',
                        color: 'border-t-blue',
                        textColor: 'text-navy',
                        bg: 'bg-white'
                    },
                    {
                        title: "Total AI Disallowed",
                        value: `₹${totalDisallowed.toFixed(2)} Cr`,
                        sub: 'REJECTED + CAPPED TOTAL',
                        color: 'border-t-slate-800',
                        textColor: totalDisallowed > 0 ? 'text-red-600' : 'text-slate-600',
                        bg: totalDisallowed > 0 ? 'bg-red-50/30' : 'bg-white'
                    },
                ].map((stat, i) => (
                    <motion.div key={i} variants={itemVariants} whileHover={{ y: -5, scale: 1.02 }} className="transition-all duration-200">
                        <Card className={`overflow-hidden border-t-[3px] shadow-md ${stat.color} ${stat.bg}`}>
                            <CardContent className="p-5">
                                <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                                    {stat.title}
                                </div>
                                <div className={`mb-1.5 font-mono text-3xl font-bold tracking-tight ${stat.textColor}`}>
                                    {stat.value}
                                </div>
                                <div className="text-[10px] font-semibold text-slate-400">
                                    {stat.sub}
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                ))}
            </div>

            <div className="grid grid-cols-[1fr_360px] items-start gap-6 pt-2">

                {/* Main Table */}
                <motion.div variants={itemVariants} className="space-y-6">
                    <Card className="shadow-md overflow-hidden border-slate-200">
                        <CardHeader className="bg-slate-50/50 border-b px-6 py-4">
                            <CardTitle className="text-[15px] font-semibold flex items-center gap-2">
                                Line-Item Prudence Validation
                            </CardTitle>
                            <CardDescription className="text-xs">
                                Click any row to view the AI&apos;s regulatory reasoning.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="p-0">
                            <Table>
                                <TableHeader className="bg-navy text-white">
                                    <TableRow className="hover:bg-navy">
                                        <TableHead className="text-white h-11 px-6">Line Item</TableHead>
                                        <TableHead className="text-right text-white h-11">Claimed (₹ Cr)</TableHead>
                                        <TableHead className="text-right text-white h-11 font-bold">AI Allowed (₹ Cr)</TableHead>
                                        <TableHead className="text-center text-white h-11 px-6">Status</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {costHeads.map((item) => {
                                        const diff = Number(item.actual_cr) - Number(item.final_allowed_cr);
                                        const isFlagged = diff > 0.01;
                                        const isSelected = selectedItem?.id === item.id;

                                        return (
                                            <TableRow
                                                key={item.id}
                                                className={`cursor-pointer transition-colors
                                                    ${isSelected ? 'bg-blue/5 border-l-4 border-l-blue hover:bg-blue/10' : 'border-l-4 border-l-transparent'}
                                                    ${isFlagged && !isSelected ? 'hover:bg-amber-50/50' : 'hover:bg-slate-50'}
                                                `}
                                                onClick={() => setSelectedItem(item)}
                                            >
                                                <TableCell className="py-3.5 px-6 font-medium text-navy">{item.head_name}</TableCell>
                                                <TableCell className="py-3.5 text-right font-mono text-slate-600">₹ {Number(item.actual_cr).toFixed(2)}</TableCell>
                                                <TableCell className={`py-3.5 text-right font-mono font-bold ${['approved', 'partial_approval'].includes(item.final_verdict?.toLowerCase()) ? 'text-green-600' : 'text-red-600'}`}>
                                                    ₹ {Number(item.final_allowed_cr).toFixed(2)}
                                                </TableCell>
                                                <TableCell className="py-3.5 px-6 text-center">
                                                    {item.final_verdict?.toLowerCase() === 'capped' ? (
                                                        <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider bg-red-50 text-red-700 border-red-200">
                                                            <AlertTriangle className="mr-1 h-3 w-3" /> Capped
                                                        </Badge>
                                                    ) : item.final_verdict?.toLowerCase() === 'rejected' ? (
                                                        <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider bg-red-100 text-red-900 border-red-300">
                                                            <XCircle className="mr-1 h-3 w-3" /> Rejected
                                                        </Badge>
                                                    ) : item.final_verdict?.toLowerCase() === 'partial_approval' ? (
                                                        <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider bg-amber-50 text-amber-700 border-amber-200">
                                                            <Info className="mr-1 h-3 w-3" /> Partial
                                                        </Badge>
                                                    ) : (
                                                        <Badge variant="outline" className="text-[10px] uppercase font-bold tracking-wider bg-green-50 text-green-700 border-green-200 pt-0.5">
                                                            <CheckCircle2 className="mr-1 h-3 w-3" /> Approved
                                                        </Badge>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        )
                                    })}
                                </TableBody>
                            </Table>
                            <div className="flex items-center justify-between border-t bg-slate-50 px-6 py-3">
                                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Total Disallowed Amount</span>
                                <span className="font-mono font-bold text-red-600 text-base">₹ {totalDisallowed.toFixed(2)} Cr</span>
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>

                {/* Right Column: Reasoning Drilldown & Summary */}
                <motion.div variants={itemVariants} className="space-y-6">

                    <AnimatePresence mode="popLayout">
                        {selectedItem ? (
                            <motion.div
                                key="drilldown"
                                initial={{ opacity: 0, x: 20, scale: 0.95 }}
                                animate={{ opacity: 1, x: 0, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                                transition={{ type: "spring", stiffness: 350, damping: 25 }}
                            >
                                <Card className="shadow-lg border-blue shadow-blue/10 relative overflow-hidden">
                                    <div className="absolute top-0 left-0 w-1 h-full bg-blue"></div>
                                    <CardHeader className="bg-slate-50 border-b px-5 py-4 flex flex-row items-center justify-between space-y-0">
                                        <CardTitle className="text-[14px] font-bold text-navy flex items-center gap-2">
                                            <Info className="h-4 w-4 text-blue" />
                                            AI Reasoning Details
                                        </CardTitle>
                                        <button
                                            onClick={() => setSelectedItem(null)}
                                            className="rounded-full bg-slate-200/50 p-1.5 text-slate-500 hover:bg-slate-200 hover:text-navy transition-colors"
                                        >
                                            <XCircle size={16} />
                                        </button>
                                    </CardHeader>
                                    <CardContent className="p-5 space-y-5">
                                        <div>
                                            <div className="text-[15px] font-bold text-navy mb-1">{selectedItem.head_name}</div>
                                            <div className="flex items-center gap-3 text-sm font-mono mt-2 p-3 bg-slate-50 rounded-md border text-slate-600">
                                                <div className="flex-1 text-center border-r border-slate-200">Claimed<br /><span className="font-bold text-navy">₹{Number(selectedItem.actual_cr).toFixed(2)}</span></div>
                                                <div className="flex-1 text-center">Allowed<br /><span className={`font-bold ${Number(selectedItem.actual_cr) > Number(selectedItem.final_allowed_cr) ? 'text-red-600' : 'text-green-600'}`}>₹{Number(selectedItem.final_allowed_cr).toFixed(2)}</span></div>
                                            </div>
                                        </div>

                                        <div className="space-y-4 relative before:absolute before:inset-0 before:ml-3 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
                                            {/* Step 1 */}
                                            <div className="relative flex items-start gap-4">
                                                <div className="flex items-center justify-center w-7 h-7 text-[11px] font-bold text-white bg-navy rounded-full ring-4 ring-white z-10 shrink-0 shadow-sm">
                                                    1
                                                </div>
                                                <div className="flex-1 rounded-md bg-white border p-3 shadow-sm relative pt-4">
                                                    <span className="absolute -top-2.5 left-3 bg-white px-1.5 text-[9px] font-bold uppercase tracking-widest text-muted-foreground">KSERC Regulation</span>
                                                    <div className="font-mono text-[12px] text-slate-700 leading-relaxed whitespace-pre-wrap">
                                                        {selectedItem.ai_order_reference || 'Normative escalation limits strictly enforced against prior approved ARR base.'}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Step 2 */}
                                            <div className="relative flex items-start gap-4">
                                                <div className="flex items-center justify-center w-7 h-7 text-[11px] font-bold text-white bg-blue rounded-full ring-4 ring-white z-10 shrink-0 shadow-sm mt-1">
                                                    2
                                                </div>
                                                <div className="flex-1">
                                                    <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground ml-1 mb-1 block">Decision Rationale</span>
                                                    <div className="text-[13.5px] text-slate-800 leading-relaxed bg-blue/5 p-3 rounded-md border border-blue/10">
                                                        {selectedItem.ai_reason}
                                                    </div>

                                                    {Number(selectedItem.actual_cr) > Number(selectedItem.final_allowed_cr) && (
                                                        <div className="mt-3 text-red-700 bg-red-50 border border-red-100 p-2.5 rounded-md text-[13px] font-semibold flex items-center justify-between shadow-sm">
                                                            <span>Total Disallowed:</span>
                                                            <span className="font-mono">
                                                                ₹{(Number(selectedItem.actual_cr) - Number(selectedItem.final_allowed_cr)).toFixed(2)} Cr
                                                            </span>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </CardContent>
                                    <div className="bg-slate-50 border-t p-3 flex justify-end gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => {
                                                setModifyValue(selectedItem.final_allowed_cr.toString());
                                                setModifyVerdict(selectedItem.final_verdict.toLowerCase());
                                                setModifyNote("");
                                                setIsModifyModalOpen(true);
                                            }}
                                            className="text-xs h-8 hover:bg-slate-200"
                                        >
                                            Modify Value manually
                                        </Button>
                                    </div>
                                </Card>
                            </motion.div>
                        ) : (
                            <motion.div
                                key="summary"
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                transition={{ duration: 0.2 }}
                            >
                                <Card className="shadow-md">
                                    <CardHeader className="border-b px-5 py-4 bg-slate-50/50">
                                        <CardTitle className="text-[14px]">Revenue Gap Overview</CardTitle>
                                    </CardHeader>
                                    <CardContent className="p-0">
                                        <table className="w-full text-[13.5px]">
                                            <tbody>
                                                <tr className="border-b bg-white">
                                                    <td className="py-3 px-5 text-slate-600">Approved ARR<br /><span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Total Commission Allowance</span></td>
                                                    <td className="py-3 px-5 text-right font-mono font-bold text-blue text-[15px]">₹ {caseData.actual_arr_cr?.toFixed(2)}</td>
                                                </tr>
                                                <tr className="border-b bg-white">
                                                    <td className="py-3 px-5 text-slate-600">Actual Revenue<br /><span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Realized from standard tariff</span></td>
                                                    <td className="py-3 px-5 text-right font-mono font-bold text-green-600 text-[15px]">₹ {caseData.revenue_actual_cr?.toFixed(2)}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                        <div className={`p-4 ${isGap ? 'bg-red-50' : 'bg-green-50'}`}>
                                            <div className="flex justify-between items-center mb-1">
                                                <span className={`text-[11px] font-bold uppercase tracking-widest ${isGap ? 'text-red-700' : 'text-green-700'}`}>
                                                    {isGap ? 'Final Under-Recovery' : 'Final Over-Recovery'}
                                                </span>
                                            </div>
                                            <div className={`text-right font-mono text-3xl font-bold ${isGap ? 'text-red-700' : 'text-green-700'}`}>
                                                ₹ {Math.abs(gap).toFixed(2)} Cr
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Ask AI Chat Box (Always Visible beneath) */}
                    <Card className="shadow-md overflow-hidden border-slate-300">
                        <CardHeader className="bg-navy px-4 py-3 flex flex-row items-center gap-2.5">
                            <div className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                            </div>
                            <CardTitle className="font-serif text-[13px] font-semibold text-white tracking-wide">
                                KSERC-Analyst Chat
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0 flex flex-col bg-slate-50">
                            <div className="h-[200px] overflow-y-auto p-4 space-y-3">
                                {chatMessages.map((msg, i) => (
                                    <div key={i} className={`max-w-[90%] text-[13px] leading-relaxed shadow-sm px-3.5 py-2.5 border ${msg.role === 'assistant'
                                        ? 'self-start rounded-b-xl rounded-tr-xl border-slate-200 bg-white'
                                        : 'self-end rounded-b-xl rounded-tl-xl border-blue/30 bg-blue/5 ml-auto'
                                        }`}>
                                        {msg.role === 'assistant' && <div className="mb-1 text-[9px] font-bold uppercase tracking-[1px] text-blue">KSERC-Analyst System</div>}
                                        {msg.role === 'user' && <div className="mb-1 text-[9px] font-bold uppercase tracking-[1px] text-navy">You</div>}
                                        {msg.content}
                                    </div>
                                ))}
                                {chatLoading && (
                                    <div className="text-xs text-muted-foreground animate-pulse italic ml-2">Analyst is typing...</div>
                                )}
                            </div>
                            <div className="flex border-t bg-white p-2 gap-2">
                                <input
                                    type="text"
                                    placeholder="e.g. Why was Employee Cost capped?"
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                                    className="flex-1 rounded-md border-slate-200 bg-slate-50 px-3 py-2 text-[13px] outline-none transition-colors focus:border-blue focus:bg-white focus:ring-1 focus:ring-blue"
                                />
                                <Button size="sm" onClick={handleSendMessage} disabled={chatLoading} className="bg-navy hover:bg-navy-dark px-3 rounded-md shadow-sm">
                                    <Send size={14} />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>
            </div>

            {/* Modify Modal */}
            {isModifyModalOpen && selectedItem && (
                <div className="fixed inset-0 z-[200] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="w-[400px] bg-white rounded-xl shadow-2xl border overflow-hidden">
                        <div className="bg-navy px-4 py-3 text-white font-semibold flex justify-between items-center">
                            <span>Modify Expense Value</span>
                            <button onClick={() => setIsModifyModalOpen(false)} className="text-white/70 hover:text-white"><XCircle size={18} /></button>
                        </div>
                        <div className="p-5 space-y-4">
                            <div>
                                <label className="text-xs font-semibold text-slate-500 uppercase tracking-widest block mb-1.5">Cost Head</label>
                                <div className="font-medium text-navy bg-slate-50 p-2 rounded-md border">{selectedItem.head_name}</div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs font-semibold text-slate-500 uppercase tracking-widest block mb-1.5">Claimed (₹ Cr)</label>
                                    <div className="font-mono bg-slate-50 p-2 rounded-md border text-slate-500">{selectedItem.actual_cr.toFixed(2)}</div>
                                </div>
                                <div>
                                    <label className="text-xs font-bold text-navy uppercase tracking-widest block mb-1.5">New Target Allowed (₹ Cr)</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={modifyValue}
                                        onChange={e => setModifyValue(e.target.value)}
                                        className="w-full font-mono bg-white p-2 rounded-md border border-blue focus:ring-1 focus:ring-blue outline-none"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs font-bold text-navy uppercase tracking-widest block mb-1.5">Current Verdict</label>
                                    <div className="bg-slate-50 p-2 rounded-md border text-slate-500 text-sm capitalize">{selectedItem.final_verdict}</div>
                                </div>
                                <div>
                                    <label className="text-xs font-bold text-navy uppercase tracking-widest block mb-1.5">New Verdict</label>
                                    <Select value={modifyVerdict} onValueChange={setModifyVerdict}>
                                        <SelectTrigger className="h-10 bg-white border-blue/40 ring-offset-background focus:ring-1 focus:ring-blue">
                                            <SelectValue placeholder="Override verdict" />
                                        </SelectTrigger>
                                        <SelectContent className="z-[300] bg-white border shadow-xl">
                                            <SelectItem value="approved">Approved</SelectItem>
                                            <SelectItem value="capped">Capped</SelectItem>
                                            <SelectItem value="rejected">Rejected</SelectItem>
                                            <SelectItem value="partial_approval">Partial Approval</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                            <div>
                                <label className="text-xs font-bold text-navy uppercase tracking-widest block mb-1.5">Reviewer Note (Required)</label>
                                <textarea
                                    value={modifyNote}
                                    onChange={e => setModifyNote(e.target.value)}
                                    placeholder="Explain why this value is being overridden..."
                                    className="w-full h-24 text-sm bg-white p-2 rounded-md border focus:border-blue focus:ring-1 focus:ring-blue outline-none resize-none"
                                />
                            </div>
                        </div>
                        <div className="bg-slate-50 border-t p-4 flex justify-end gap-2">
                            <Button variant="ghost" onClick={() => setIsModifyModalOpen(false)}>Cancel</Button>
                            <Button className="bg-navy hover:bg-navy-dark" disabled={isModifying || !modifyValue || !modifyNote} onClick={handleModifyValue}>
                                {isModifying ? "Saving..." : "Save Changes"}
                            </Button>
                        </div>
                    </motion.div>
                </div>
            )}
        </motion.div>
    );
}

// Chevron icon missing in imports
function ChevronRight(props: any) {
    return <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m9 18 6-6-6-6" /></svg>
}

export default function ResultsPage() {
    return (
        <Suspense fallback={<div className="p-12 text-center animate-pulse font-medium text-navy">Loading Analysis Engine...</div>}>
            <ResultsContent />
        </Suspense>
    );
}
