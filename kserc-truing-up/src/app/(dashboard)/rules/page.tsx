"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Save, FileText, CheckCircle2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function RulesPage() {
    const { toast } = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const [rules, setRules] = useState({
        new_rules: "",
        tariff_data: "",
        historical_data: ""
    });

    useEffect(() => {
        fetch("/api/rules")
            .then(res => res.json())
            .then(data => {
                if (data && !data.error) {
                    setRules({
                        new_rules: data.new_rules || "",
                        tariff_data: data.tariff_data || "",
                        historical_data: data.historical_data || ""
                    });
                }
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const handleSave = async () => {
        setSaving(true);
        try {
            const res = await fetch("/api/rules", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(rules)
            });

            if (res.ok) {
                toast({
                    title: "Knowledge Base Updated",
                    description: "The AI context rules have been successfully saved.",
                    variant: "default",
                });
            } else {
                throw new Error("Failed to save rules");
            }
        } catch (e) {
            toast({
                title: "Error saving",
                description: "There was a problem saving the Knowledge Base.",
                variant: "destructive",
            });
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <div className="p-8 animate-pulse text-navy font-medium">Loading Knowledge Base Data...</div>;
    }

    return (
        <div className="mx-auto max-w-5xl space-y-6 pt-4 pb-12 animate-in fade-in">
            <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-navy mb-1 leading-none">
                        Knowledge Base Configuration
                    </h1>
                    <p className="text-[14px] text-muted-foreground font-medium mt-2">
                        Manage the regulatory context used by the KSERC AI Analyst for reasoning.
                    </p>
                </div>
                <Button
                    onClick={handleSave}
                    disabled={saving}
                    className="bg-navy hover:bg-navy-dark shadow-md"
                >
                    {saving ? (
                        <>Saving...</>
                    ) : (
                        <><Save className="mr-2 h-4 w-4" /> Save Configuration</>
                    )}
                </Button>
            </div>

            <div className="space-y-6">
                <Card className="shadow-sm border-slate-200">
                    <CardHeader className="bg-slate-50/50 border-b pb-4">
                        <div className="flex items-center gap-2">
                            <FileText className="text-blue h-5 w-5" />
                            <CardTitle className="text-[16px]">1. New Rules & Regulations (2026)</CardTitle>
                        </div>
                        <CardDescription>
                            Latest norms and standards governing the truing-up process.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="p-5">
                        <Textarea
                            value={rules.new_rules}
                            onChange={(e) => setRules({ ...rules, new_rules: e.target.value })}
                            className="min-h-[250px] text-sm leading-relaxed p-4 bg-slate-50/30"
                            placeholder="Paste preprocessed text from Electricity Act/Regulations here..."
                        />
                    </CardContent>
                </Card>

                <Card className="shadow-sm border-slate-200">
                    <CardHeader className="bg-slate-50/50 border-b pb-4">
                        <div className="flex items-center gap-2">
                            <FileText className="text-amber-600 h-5 w-5" />
                            <CardTitle className="text-[16px]">2. Tariff Related Data</CardTitle>
                        </div>
                        <CardDescription>
                            Current tariff orders, normative parameters, and financial benchmarks.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="p-5">
                        <Textarea
                            value={rules.tariff_data}
                            onChange={(e) => setRules({ ...rules, tariff_data: e.target.value })}
                            className="min-h-[250px] text-sm leading-relaxed p-4 bg-slate-50/30"
                            placeholder="Paste preprocessed Tariff Data here..."
                        />
                    </CardContent>
                </Card>

                <Card className="shadow-sm border-slate-200">
                    <CardHeader className="bg-slate-50/50 border-b pb-4">
                        <div className="flex items-center gap-2">
                            <FileText className="text-green-600 h-5 w-5" />
                            <CardTitle className="text-[16px]">3. Historical Precedents</CardTitle>
                        </div>
                        <CardDescription>
                            Extreme cases and past approved deviations to guide the AI&apos;s judgment.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="p-5">
                        <Textarea
                            value={rules.historical_data}
                            onChange={(e) => setRules({ ...rules, historical_data: e.target.value })}
                            className="min-h-[250px] text-sm leading-relaxed p-4 bg-slate-50/30"
                            placeholder="Paste preprocessed historical cases here..."
                        />
                    </CardContent>
                </Card>
            </div>

            <div className="bg-blue/5 border border-blue/20 rounded-md p-4 flex items-start gap-3 mt-8">
                <CheckCircle2 className="text-blue mt-0.5" size={18} />
                <div className="text-sm text-slate-700">
                    <strong>Note:</strong> The AI tool automatically references these text blocks during the Prudence Validation stage in the generated reports. Editing these values will instantly update the reasoning applied to future analyses.
                </div>
            </div>
        </div>
    );
}
