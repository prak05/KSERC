"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, WidthType, BorderStyle, AlignmentType } from "docx";
import { AlertTriangle, Download, ArrowLeft, CheckCircle2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

function ReportContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const caseId = searchParams.get("caseId");

    const [loading, setLoading] = useState(true);
    const [caseData, setCaseData] = useState<Record<string, any> | null>(null);
    const [costHeads, setCostHeads] = useState<any[]>([]);
    const [revenue, setRevenue] = useState<Record<string, any> | null>(null);
    const [reportText, setReportText] = useState("");
    const [generatingText, setGeneratingText] = useState(false);

    const [preparedBy, setPreparedBy] = useState("KSERC Analytical Officer");
    const [orderDate, setOrderDate] = useState(new Date().toISOString().split('T')[0]);
    const [remarks, setRemarks] = useState("");

    useEffect(() => {
        // eslint-disable-next-line react-hooks/exhaustive-deps
        const fetchData = async () => {
            try {
                setLoading(true);
                const resultsRes = await fetch(`/api/get-results?caseId=${caseId}`);
                if (!resultsRes.ok) throw new Error("Failed to fetch results");
                const { cData, chData, revData } = await resultsRes.json();

                setCaseData(cData);
                setCostHeads(chData || []);
                setRevenue(revData);

                // Generate narrative
                setGeneratingText(true);
                const res = await fetch("/api/report", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ caseId: caseId })
                });
                const data = await res.json();
                if (res.ok) setReportText(data.report_text);

            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
                setGeneratingText(false);
            }
        };

        if (caseId) {
            fetchData();
        } else {
            setLoading(false);
        }
    }, [caseId]);

    const downloadPDF = () => {
        const doc = new jsPDF();
        const isGap = (caseData?.revenue_gap_cr || 0) > 0;

        // Title
        doc.setFont("times", "bold");
        doc.setFontSize(14);
        doc.text("KERALA STATE ELECTRICITY REGULATORY COMMISSION", 105, 20, { align: "center" });

        doc.setFontSize(11);
        doc.text("THIRUVANANTHAPURAM", 105, 26, { align: "center" });

        // Members Present
        doc.setFont("times", "bold");
        doc.setFontSize(10);
        doc.text("Present:", 105, 36, { align: "center" });
        doc.setFont("times", "normal");
        doc.text("Shri. T.K. Jose, Chairman", 105, 41, { align: "center" });
        doc.text("Adv. A.J. Wilson, Member", 105, 46, { align: "center" });
        doc.text("Shri. B. Pradeep, Member", 105, 51, { align: "center" });

        // Separator Line
        doc.setLineWidth(0.5);
        doc.line(14, 55, 196, 55);

        // Details
        doc.setFont("times", "normal");
        doc.text(`Petition No.: OP No. __ / ${new Date(orderDate).getFullYear()}`, 14, 62);
        doc.text(`Date of Order: ${orderDate.split('-').reverse().join('-')}`, 14, 67);

        doc.setFont("times", "bold");
        doc.text("In the Matter Of:", 14, 76);

        doc.setFont("times", "normal");
        const matterText = `Petition filed by M/s ${caseData?.licensees?.name || ''} for the Truing Up of Accounts for the Financial Year ${caseData?.financial_year || ''}.`;
        const splitMatter = doc.splitTextToSize(matterText, 180);
        doc.text(splitMatter, 14, 81);

        const afterHeaderY = 81 + (splitMatter.length * 5) + 8;

        // 1. Component-wise Analysis
        doc.setFont("times", "bold");
        doc.text("1. Component-wise Analysis (₹ Crore)", 14, afterHeaderY);

        const tableBody1 = costHeads.map(h => {
            const verdict = h.final_verdict ? h.final_verdict.toUpperCase() : (Number(h.final_allowed_cr) > 0 && Number(h.final_allowed_cr) < Number(h.actual_cr) ? 'PARTIAL APPROVAL' : (Number(h.final_allowed_cr) === 0 ? 'REJECTED' : 'APPROVED'));
            const reason = (h.is_override ? "[ADMIN OVERRIDE] " : "") + (h.ai_reason || "As per normative limits.");
            return [
                h.head_name,
                Number(h.actual_cr || 0).toFixed(2),
                Number(h.final_allowed_cr || 0).toFixed(2),
                (Number(h.actual_cr || 0) - Number(h.final_allowed_cr || 0)).toFixed(2),
                verdict,
                reason
            ];
        });

        autoTable(doc, {
            startY: 65,
            head: [['Cost Head', 'Claimed (Cr)', 'Allowed (Cr)', 'Disallowed (Cr)', 'Verdict', 'Reasoning']],
            body: tableBody1,
            theme: 'grid',
            headStyles: { fillColor: [26, 53, 87] },
            styles: { fontSize: 8, font: 'times' },
            columnStyles: {
                0: { cellWidth: 30 },
                1: { cellWidth: 20 },
                2: { cellWidth: 20 },
                3: { cellWidth: 20 },
                4: { cellWidth: 25 },
                5: { cellWidth: 'auto' }
            }
        });

        const finalY1 = (doc as Record<string, any>).lastAutoTable.finalY + 15;

        // 2. Controllable vs Uncontrollable Breakup
        doc.setFont("times", "bold");
        doc.text("2. Controllable vs. Uncontrollable Expenses (₹ Crore)", 14, finalY1);

        const controllableCategories = ["O&M", "Admin", "Employee", "A&G", "Repair"];
        const controllable = costHeads.filter(h => controllableCategories.some(c => h.head_name.includes(c) || h.category?.includes(c)));
        const uncontrollable = costHeads.filter(h => !controllable.includes(h));

        const getTableRows = (arr: any[]) => arr.map(h => [
            h.head_name,
            Number(h.actual_cr || 0).toFixed(2),
            Number(h.final_allowed_cr || 0).toFixed(2),
            (Number(h.actual_cr || 0) - Number(h.final_allowed_cr || 0)).toFixed(2)
        ]);

        autoTable(doc, {
            startY: finalY1 + 5,
            head: [['Type / Cost Head', 'Claimed (Cr)', 'Allowed (Cr)', 'Disallowed (Cr)']],
            body: [
                [{ content: 'CONTROLLABLE EXPENSES', colSpan: 4, styles: { fillColor: [240, 240, 240], fontStyle: 'bold' } }],
                ...getTableRows(controllable),
                [{ content: 'UNCONTROLLABLE EXPENSES', colSpan: 4, styles: { fillColor: [240, 240, 240], fontStyle: 'bold' } }],
                ...getTableRows(uncontrollable),
            ],
            theme: 'grid',
            headStyles: { fillColor: [26, 53, 87] },
            styles: { fontSize: 8, font: 'times' }
        });

        const finalY2 = (doc as Record<string, any>).lastAutoTable.finalY + 15;

        // Financial Totals
        doc.setFont("times", "bold");
        doc.text("3. Revenue Gap Computation (₹ Crore)", 14, finalY2);

        autoTable(doc, {
            startY: finalY2 + 5,
            head: [['Parameter', 'Amount (Cr)']],
            body: [
                ['Net Approved ARR', Number(caseData?.actual_arr_cr || 0).toFixed(2)],
                ['Actual Revenue Collected', Number(caseData?.revenue_actual_cr || 0).toFixed(2)],
                [`Revenue ${isGap ? 'Gap' : 'Surplus'}`, Math.abs(caseData?.revenue_gap_cr || 0).toFixed(2)]
            ],
            theme: 'grid',
            headStyles: { fillColor: [26, 53, 87] },
            styles: { fontSize: 9, font: 'times' }
        });

        let currentY = (doc as Record<string, any>).lastAutoTable.finalY + 15;

        // 4. Commission's Observations, Directions & Narrative
        if (currentY > 250) {
            doc.addPage();
            currentY = 20;
        }
        doc.setFont("times", "bold");
        doc.text("4. Commission's Observations, Directions & Narrative", 14, currentY);
        doc.setFont("times", "normal");

        currentY += 8;
        const textToPrint = reportText + (remarks ? `\n\nRemarks: ${remarks}` : '');
        const lines = textToPrint.split('\n');

        lines.forEach(line => {
            if (currentY > 280) {
                doc.addPage();
                currentY = 20;
            }
            if (line.trim().startsWith('## ') || line.trim().startsWith('### ')) {
                doc.setFont("times", "bold");
                const cleanLine = line.replace(/^#+\s/, '');
                const splitHead = doc.splitTextToSize(cleanLine, 180);
                doc.text(splitHead, 14, currentY);
                currentY += splitHead.length * 5 + 2;
            } else if (line.trim() === '') {
                currentY += 3;
            } else {
                doc.setFont("times", "normal");
                const cleanLine = line.replace(/\*\*/g, '');
                const splitLine = doc.splitTextToSize(cleanLine, 180);
                doc.text(splitLine, 14, currentY);
                currentY += splitLine.length * 5 + 1;
            }
        });

        // Add Signature Block
        currentY += 15;
        if (currentY > 260) {
            doc.addPage();
            currentY = 20;
        }

        doc.setFont("times", "bold");
        doc.text("Sd/-", 40, currentY, { align: "center" });
        doc.text("Adv. A.J. Wilson", 40, currentY + 5, { align: "center" });
        doc.text("Member", 40, currentY + 10, { align: "center" });

        doc.text("Sd/-", 170, currentY, { align: "center" });
        doc.text("B. Pradeep", 170, currentY + 5, { align: "center" });
        doc.text("Member", 170, currentY + 10, { align: "center" });

        currentY += 25;
        doc.text("Sd/-", 105, currentY, { align: "center" });
        doc.text("T.K. Jose", 105, currentY + 5, { align: "center" });
        doc.text("Chairman", 105, currentY + 10, { align: "center" });

        currentY += 25;
        if (currentY > 270) {
            doc.addPage();
            currentY = 20;
        }

        doc.setFont("times", "bold");
        doc.text("Approved for issue", 105, currentY, { align: "center" });

        currentY += 20;
        doc.setFont("times", "normal");
        doc.text("Sd/-", 105, currentY, { align: "center" });
        doc.setFont("times", "bold");
        doc.text("Secretary", 105, currentY + 5, { align: "center" });

        currentY += 15;
        doc.setLineWidth(0.5);
        doc.setDrawColor(150, 150, 150);
        doc.line(14, currentY, 196, currentY);

        doc.setFont("times", "italic");
        doc.setFontSize(9);
        doc.setTextColor(100, 100, 100);
        doc.text(`Order dated ${orderDate.split('-').reverse().join(' ')}`, 105, currentY + 6, { align: "center" });

        doc.save(`KSERC_TruingUp_Order_${(caseData?.financial_year || '').replace('-', '_')}.pdf`);
    };

    const downloadDOCX = async () => {
        const createHeaderCell = (text: string) => new TableCell({ children: [new Paragraph({ children: [new TextRun({ text, bold: true })] })] });
        const createCell = (text: string) => new TableCell({ children: [new Paragraph({ text })] });

        const controllableCategories = ["O&M", "Admin", "Employee", "A&G", "Repair"];
        const controllable = costHeads.filter(h => controllableCategories.some(c => h.head_name.includes(c) || h.category?.includes(c)));
        const uncontrollable = costHeads.filter(h => !controllable.includes(h));
        const isGap = (caseData?.revenue_gap_cr || 0) > 0;

        const getDocxTableRows = (arr: any[]) => arr.map(h => new TableRow({
            children: [
                createCell(h.head_name),
                createCell(Number(h.actual_cr || 0).toFixed(2)),
                createCell(Number(h.final_allowed_cr || 0).toFixed(2)),
                createCell((Number(h.actual_cr || 0) - Number(h.final_allowed_cr || 0)).toFixed(2))
            ]
        }));

        const doc = new Document({
            sections: [{
                properties: {},
                children: [
                    new Paragraph({ text: "KERALA STATE ELECTRICITY REGULATORY COMMISSION", heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER }),
                    new Paragraph({ text: `TRUING-UP ORDER: FY ${caseData?.financial_year || ''}`, heading: HeadingLevel.HEADING_2, alignment: AlignmentType.CENTER }),
                    new Paragraph({ text: "" }),
                    new Paragraph({ text: `Licensee: ${caseData?.licensees?.name || ''}` }),
                    new Paragraph({ text: `Order Date: ${orderDate}` }),
                    new Paragraph({ text: `Prepared By: ${preparedBy}` }),
                    new Paragraph({ text: "" }),

                    new Paragraph({ text: "1. Component-wise Analysis (₹ Crore)", heading: HeadingLevel.HEADING_3 }),
                    new Table({
                        width: { size: 100, type: WidthType.PERCENTAGE },
                        rows: [
                            new TableRow({
                                children: [
                                    createHeaderCell("Cost Head"),
                                    createHeaderCell("Claimed (Cr)"),
                                    createHeaderCell("Allowed (Cr)"),
                                    createHeaderCell("Disallowed (Cr)"),
                                    createHeaderCell("Verdict"),
                                    createHeaderCell("Reasoning")
                                ]
                            }),
                            ...costHeads.map(h => {
                                const verdict = h.final_verdict ? h.final_verdict.toUpperCase() : (Number(h.final_allowed_cr) > 0 && Number(h.final_allowed_cr) < Number(h.actual_cr) ? 'PARTIAL APPROVAL' : (Number(h.final_allowed_cr) === 0 ? 'REJECTED' : 'APPROVED'));
                                const reason = (h.is_override ? "[ADMIN OVERRIDE] " : "") + (h.ai_reason || "As per normative limits.");
                                return new TableRow({
                                    children: [
                                        createCell(h.head_name),
                                        createCell(Number(h.actual_cr || 0).toFixed(2)),
                                        createCell(Number(h.final_allowed_cr || 0).toFixed(2)),
                                        createCell((Number(h.actual_cr || 0) - Number(h.final_allowed_cr || 0)).toFixed(2)),
                                        createCell(verdict),
                                        createCell(reason)
                                    ]
                                });
                            })
                        ]
                    }),
                    new Paragraph({ text: "" }),

                    new Paragraph({ text: "2. Controllable vs. Uncontrollable Expenses (₹ Crore)", heading: HeadingLevel.HEADING_3 }),
                    new Table({
                        width: { size: 100, type: WidthType.PERCENTAGE },
                        rows: [
                            new TableRow({
                                children: [
                                    createHeaderCell("Type / Cost Head"),
                                    createHeaderCell("Claimed (Cr)"),
                                    createHeaderCell("Allowed (Cr)"),
                                    createHeaderCell("Disallowed (Cr)")
                                ]
                            }),
                            new TableRow({ children: [new TableCell({ columnSpan: 4, children: [new Paragraph({ children: [new TextRun({ text: "CONTROLLABLE EXPENSES", bold: true })] })] })] }),
                            ...getDocxTableRows(controllable),
                            new TableRow({ children: [new TableCell({ columnSpan: 4, children: [new Paragraph({ children: [new TextRun({ text: "UNCONTROLLABLE EXPENSES", bold: true })] })] })] }),
                            ...getDocxTableRows(uncontrollable)
                        ]
                    }),
                    new Paragraph({ text: "" }),

                    new Paragraph({ text: "3. Revenue Gap Computation (₹ Crore)", heading: HeadingLevel.HEADING_3 }),
                    new Table({
                        width: { size: 100, type: WidthType.PERCENTAGE },
                        rows: [
                            new TableRow({ children: [createHeaderCell("Parameter"), createHeaderCell("Amount (Cr)")] }),
                            new TableRow({ children: [createCell("Net Approved ARR"), createCell(Number(caseData?.actual_arr_cr || 0).toFixed(2))] }),
                            new TableRow({ children: [createCell("Actual Revenue Collected"), createCell(Number(caseData?.revenue_actual_cr || 0).toFixed(2))] }),
                            new TableRow({ children: [createCell(`Revenue ${isGap ? 'Gap' : 'Surplus'}`), createCell(Math.abs(caseData?.revenue_gap_cr || 0).toFixed(2))] }),
                        ]
                    }),
                    new Paragraph({ text: "" }),

                    new Paragraph({ text: "4. Commission's Observations, Directions & Narrative", heading: HeadingLevel.HEADING_3 }),
                    ...(reportText + (remarks ? `\n\nRemarks: ${remarks}` : '')).split('\n').map(line => {
                        const isHeading = line.trim().startsWith('##');
                        const cleanLine = line.replace(/^#+\s/, '').replace(/\*\*/g, '');
                        if (line.trim() === '') return new Paragraph({ text: "" });
                        return new Paragraph({
                            heading: isHeading ? HeadingLevel.HEADING_4 : undefined,
                            children: [new TextRun({ text: cleanLine, bold: isHeading })]
                        });
                    }),

                    new Paragraph({ text: "" }),
                    new Paragraph({ text: "" }),
                    new Paragraph({ text: "" }),

                    // Signature Block
                    new Table({
                        width: { size: 100, type: WidthType.PERCENTAGE },
                        borders: {
                            top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
                            bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
                            left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
                            right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
                            insideHorizontal: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
                            insideVertical: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
                        },
                        rows: [
                            new TableRow({
                                children: [
                                    new TableCell({
                                        children: [
                                            new Paragraph({ children: [new TextRun({ text: "Sd/-", bold: true })], alignment: AlignmentType.CENTER }),
                                            new Paragraph({ children: [new TextRun({ text: "Adv. A.J. Wilson", bold: true })], alignment: AlignmentType.CENTER }),
                                            new Paragraph({ text: "Member", alignment: AlignmentType.CENTER })
                                        ],
                                        borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }
                                    }),
                                    new TableCell({
                                        children: [new Paragraph({ text: "" })],
                                        borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }
                                    }),
                                    new TableCell({
                                        children: [
                                            new Paragraph({ children: [new TextRun({ text: "Sd/-", bold: true })], alignment: AlignmentType.CENTER }),
                                            new Paragraph({ children: [new TextRun({ text: "B. Pradeep", bold: true })], alignment: AlignmentType.CENTER }),
                                            new Paragraph({ text: "Member", alignment: AlignmentType.CENTER })
                                        ],
                                        borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }
                                    })
                                ]
                            }),
                            new TableRow({
                                children: [
                                    new TableCell({ children: [new Paragraph({ text: "" })], borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } } }),
                                    new TableCell({
                                        children: [
                                            new Paragraph({ text: "" }),
                                            new Paragraph({ text: "" }),
                                            new Paragraph({ children: [new TextRun({ text: "Sd/-", bold: true })], alignment: AlignmentType.CENTER }),
                                            new Paragraph({ children: [new TextRun({ text: "T.K. Jose", bold: true })], alignment: AlignmentType.CENTER }),
                                            new Paragraph({ text: "Chairman", alignment: AlignmentType.CENTER })
                                        ],
                                        borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }
                                    }),
                                    new TableCell({ children: [new Paragraph({ text: "" })], borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } } }),
                                ]
                            })
                        ]
                    }),

                    new Paragraph({ text: "" }),
                    new Paragraph({ text: "" }),
                    new Paragraph({ children: [new TextRun({ text: "Approved for issue", bold: true })], alignment: AlignmentType.CENTER }),
                    new Paragraph({ text: "" }),
                    new Paragraph({ text: "Sd/-", alignment: AlignmentType.CENTER }),
                    new Paragraph({ children: [new TextRun({ text: "Secretary", bold: true })], alignment: AlignmentType.CENTER }),
                ],
            }],
        });

        const blob = await Packer.toBlob(doc);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `KSERC_TruingUp_Order_${(caseData?.financial_year || '').replace('-', '_')}.docx`;
        a.click();
    };

    if (loading) return <div className="p-8">Loading Report Data...</div>;

    if (!caseId || !caseData) {
        return (
            <div className="p-8 space-y-4 animate-in fade-in">
                <div className="flex items-start gap-3 rounded border border-amber-200 bg-amber-50 p-4 text-amber-900">
                    <AlertTriangle className="mt-0.5" size={18} />
                    <div>
                        <strong>No analysis results found.</strong>
                        <p className="text-sm mt-1">Please select a case to generate a report for, or run a new analysis.</p>
                        <Button variant="link" onClick={() => router.push("/")} className="px-0 mt-2 text-amber-700 font-semibold p-0 h-auto">
                            Run an analysis first →
                        </Button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="animate-in fade-in space-y-4">
            <div className="mb-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                <button onClick={() => router.push("/")} className="hover:text-blue transition-colors">Home</button>
                <span>›</span>
                <button onClick={() => router.push(`/results?caseId=${caseId}`)} className="hover:text-blue transition-colors">Results</button>
                <span>›</span>
                <span className="text-foreground">Generate Report</span>
            </div>

            <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="font-serif text-[26px] font-semibold tracking-[0.2px] text-navy">
                        Generate Truing-Up Order
                    </h1>
                    <p className="mt-0.5 text-[13px] text-muted-foreground">
                        {caseData.licensees.name} — FY {caseData.financial_year}
                    </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => router.push(`/results?caseId=${caseId}`)}>
                    <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Back to Results
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-[1fr_300px] gap-4 items-start">
                <div className="space-y-4">
                    <Card>
                        <CardHeader className="border-b bg-card px-5 py-3">
                            <CardTitle className="text-[13.5px]">Report Checklist</CardTitle>
                        </CardHeader>
                        <CardContent className="p-5 flex flex-col gap-2">
                            <div className="flex items-center gap-2 text-[13.5px] text-green-700">
                                <CheckCircle2 size={16} /> Data Extracted Successfully
                            </div>
                            <div className="flex items-center gap-2 text-[13.5px] text-green-700">
                                <CheckCircle2 size={16} /> Prudence Checks Applied
                            </div>
                            <div className={`flex items-center gap-2 text-[13.5px] ${generatingText ? 'text-amber-600' : 'text-green-700'}`}>
                                {generatingText ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" /> : <CheckCircle2 size={16} />}
                                {generatingText ? 'Drafting Narrative Text via AI...' : 'Narrative Drafted'}
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader className="border-b bg-card px-5 py-3">
                            <CardTitle className="text-[13.5px]">Download Report</CardTitle>
                        </CardHeader>
                        <CardContent className="p-5">
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div className="space-y-1.5">
                                    <Label className="text-[11.5px] uppercase tracking-wider text-muted-foreground">Prepared By</Label>
                                    <Input value={preparedBy} onChange={(e) => setPreparedBy(e.target.value)} placeholder="e.g. Prakhar Sharma" />
                                </div>
                                <div className="space-y-1.5">
                                    <Label className="text-[11.5px] uppercase tracking-wider text-muted-foreground">Date of Order</Label>
                                    <Input type="date" value={orderDate} onChange={(e) => setOrderDate(e.target.value)} />
                                </div>
                            </div>
                            <div className="space-y-1.5 mb-5">
                                <Label className="text-[11.5px] uppercase tracking-wider text-muted-foreground">Additional Remarks (Optional)</Label>
                                <Textarea
                                    placeholder="Any additional commission remarks..."
                                    value={remarks}
                                    onChange={(e) => setRemarks(e.target.value)}
                                />
                            </div>

                            <div className="flex flex-col gap-2">
                                <Button disabled={generatingText} onClick={downloadPDF} className="bg-red-600 hover:bg-red-700 text-white gap-2 w-full">
                                    <Download size={16} /> Download PDF format
                                </Button>
                                <Button disabled={generatingText} onClick={downloadDOCX} className="bg-blue hover:bg-blue-light gap-2 w-full">
                                    <Download size={16} /> Download DOCX format
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                <Card>
                    <CardHeader className="border-b bg-card px-5 py-3">
                        <CardTitle className="text-[13.5px]">Session Summary</CardTitle>
                    </CardHeader>
                    <CardContent className="p-4 space-y-2 text-[13.5px]">
                        <div className="flex justify-between pb-2 border-b">
                            <span className="text-muted-foreground">Appr. ARR</span>
                            <span className="font-mono text-navy font-medium">₹ {caseData.actual_arr_cr?.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between pb-2 border-b">
                            <span className="text-muted-foreground">Revenue</span>
                            <span className="font-mono text-green-700 font-medium">₹ {caseData.revenue_actual_cr?.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between pb-2 font-bold">
                            <span>Gap / Sur.</span>
                            <span className="font-mono text-red-600">₹ {Math.abs(caseData.revenue_gap_cr)?.toFixed(2)}</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Card className="mt-4">
                <CardHeader className="border-b bg-card px-5 py-3 flex flex-row items-center justify-between space-y-0">
                    <CardTitle className="text-[13.5px]">Generated AI Narrative Review</CardTitle>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => alert("Report Text Saved Manually")} className="h-8 gap-1">
                            <Save size={14} /> Save Edits
                        </Button>
                    </div>
                </CardHeader>
                <CardContent className="p-5">
                    {generatingText ? (
                        <div className="animate-pulse flex space-x-4">
                            <div className="flex-1 space-y-4 py-1">
                                <div className="h-4 bg-slate-200 rounded w-3/4"></div>
                                <div className="space-y-2">
                                    <div className="h-4 bg-slate-200 rounded"></div>
                                    <div className="h-4 bg-slate-200 rounded w-5/6"></div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <Textarea
                            className="min-h-[300px] font-serif text-[14px] leading-relaxed resize-y"
                            value={reportText}
                            onChange={e => setReportText(e.target.value)}
                        />
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

export default function ReportPage() {
    return (
        <Suspense fallback={<div className="p-8">Loading Report...</div>}>
            <ReportContent />
        </Suspense>
    );
}
