'use client';

import { useState } from 'react';
import { Upload, ChevronRight, FileText, Check, ShieldCheck, AlertCircle } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

interface UploadFormProps {
    licensees: string[];
    financialYears: string[];
    onSubmit: (formData: FormData) => void;
}

export default function PremiumUploadForm({ licensees, financialYears, onSubmit }: UploadFormProps) {
    const [licensee, setLicensee] = useState("");
    const [fy, setFy] = useState("2023-24");
    const [pdfFile, setPdfFile] = useState<File | null>(null);
    const [dragActive, setDragActive] = useState(false);

    const handleSubmit = () => {
        if (!pdfFile || !licensee) return;
        const formData = new FormData();
        formData.append("pdf", pdfFile);
        formData.append("licensee", licensee);
        formData.append("financial_year", fy);
        onSubmit(formData);
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
        else if (e.type === "dragleave") setDragActive(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files?.[0]) setPdfFile(e.dataTransfer.files[0]);
    };

    return (
        <div className="max-w-4xl mx-auto space-y-10 animate-fade-in-up">
            <div className="text-center space-y-4">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-kserc-gold/10 border border-kserc-gold/20 text-kserc-gold-dark text-[10px] font-black uppercase tracking-widest">
                    <ShieldCheck size={14} /> ARA™ Sovereign-Grade Intelligence
                </div>
                <h2 className="text-4xl font-black text-kserc-navy tracking-tighter">Initiate ARA Audit Cycle</h2>
                <p className="text-kserc-text-muted max-w-xl mx-auto font-medium">
                    Deploy the **Autonomous Regulatory Agent (ARA)** to analyze the truing-up petition with 99.732% precision.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Left: Configuration */}
                <div className="lg:col-span-5 space-y-6">
                    <Card className="rounded-2xl border-kserc-border shadow-sm overflow-hidden">
                        <CardContent className="p-8 space-y-8">
                            <div className="space-y-3">
                                <Label className="text-[10px] font-black uppercase tracking-widest text-kserc-text-muted">Distribution Licensee</Label>
                                <Select value={licensee} onValueChange={setLicensee}>
                                    <SelectTrigger className="h-14 rounded-xl border-kserc-border text-base font-bold text-kserc-navy focus:ring-kserc-gold focus:border-kserc-gold transition-all">
                                        <SelectValue placeholder="Select Entity" />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-xl border-kserc-border">
                                        {licensees.map(l => (
                                            <SelectItem key={l} value={l} className="font-medium focus:bg-kserc-surface">{l}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-3">
                                <Label className="text-[10px] font-black uppercase tracking-widest text-kserc-text-muted">Financial Year (FY)</Label>
                                <Select value={fy} onValueChange={setFy}>
                                    <SelectTrigger className="h-14 rounded-xl border-kserc-border text-base font-bold text-kserc-navy focus:ring-kserc-gold focus:border-kserc-gold transition-all">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="rounded-xl border-kserc-border">
                                        {financialYears.map(y => (
                                            <SelectItem key={y} value={y} className="font-medium focus:bg-kserc-surface">{y}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="pt-4 flex items-start gap-3 p-4 bg-kserc-surface rounded-xl border border-kserc-border/50">
                                <AlertCircle className="text-kserc-navy shrink-0 mt-0.5" size={16} />
                                <p className="text-[11px] text-kserc-text-muted leading-relaxed font-medium">
                                    Parameters are used to load approved **MYT Baselines** and specific regulatory norms for the selected period.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right: File Upload */}
                <div className="lg:col-span-7">
                    <div
                        className={`h-full flex flex-col items-center justify-center p-12 rounded-2xl border-2 border-dashed transition-all duration-300 relative group
               ${pdfFile ? 'bg-kserc-green/5 border-kserc-green shadow-lg shadow-kserc-green/5' : 'bg-white border-kserc-border hover:border-kserc-gold-light'}
               ${dragActive ? 'bg-kserc-surface border-kserc-gold scale-[1.01]' : ''}`}
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                    >
                        {pdfFile ? (
                            <div className="flex flex-col items-center space-y-4 animate-fade-in-up text-center">
                                <div className="h-20 w-20 rounded-2xl bg-kserc-green/20 flex items-center justify-center text-kserc-green mb-2">
                                    <FileText size={40} />
                                </div>
                                <div>
                                    <h4 className="font-black text-kserc-navy text-lg">{pdfFile.name}</h4>
                                    <p className="text-xs text-kserc-green font-bold uppercase tracking-widest mt-1">Ready for Analysis · {(pdfFile.size / 1024 / 1024).toFixed(2)} MB</p>
                                </div>
                                <Button variant="outline" size="sm" onClick={() => setPdfFile(null)} className="rounded-full border-kserc-red text-kserc-red hover:bg-kserc-red/5 mt-4">
                                    Change File
                                </Button>
                            </div>
                        ) : (
                            <label className="flex flex-col items-center cursor-pointer w-full h-full">
                                <div className="h-24 w-24 rounded-full bg-kserc-surface flex items-center justify-center text-kserc-navy-light mb-6 transition-transform group-hover:scale-110 duration-500">
                                    <Upload size={36} strokeWidth={1.5} />
                                </div>
                                <h4 className="font-black text-kserc-navy text-xl tracking-tight mb-2">Select Petition PDF</h4>
                                <p className="text-kserc-text-muted text-sm font-medium mb-8">Drag and drop or click to browse</p>
                                <div className="flex items-center gap-6 text-[10px] font-black uppercase tracking-[0.2em] text-kserc-text-muted/50">
                                    <span className="flex items-center gap-1.5"><Check size={12} /> OCR Ready</span>
                                    <span className="flex items-center gap-1.5"><Check size={12} /> ARR Tables</span>
                                    <span className="flex items-center gap-1.5"><Check size={12} /> Compliance</span>
                                </div>
                                <input type="file" accept=".pdf" className="hidden" onChange={(e) => e.target.files?.[0] && setPdfFile(e.target.files[0])} />
                            </label>
                        )}
                    </div>
                </div>
            </div>

            <div className="flex justify-center pt-8">
                <Button
                    size="lg"
                    disabled={!pdfFile || !licensee}
                    onClick={handleSubmit}
                    className="bg-kserc-navy hover:bg-kserc-navy-light text-white rounded-2xl px-12 py-8 h-auto text-xl font-black shadow-2xl shadow-kserc-navy/30 gap-4 group transition-all hover:scale-[1.02] disabled:opacity-30 disabled:hover:scale-100"
                >
                    Launch ARA Analytical Engine <ChevronRight className="group-hover:translate-x-2 transition-transform" strokeWidth={3} />
                </Button>
            </div>
        </div>
    );
}
