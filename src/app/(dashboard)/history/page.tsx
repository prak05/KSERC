"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Cell
} from "recharts";
import { Download, Filter, ChevronRight, TrendingUp, TrendingDown, ArrowUpDown, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { motion } from "framer-motion";

// ── Static historical data (from .local-db.json and wireframe) ──────────
const HISTORICAL_DATA = [
    { id: "hist-1", licensee: "Technopark", year: "2020-21", claimed: 0, approved: 280.42, type: "surplus" },
    { id: "hist-2", licensee: "CSEZA", year: "2022-23", claimed: 0, approved: 135.14, type: "surplus" },
    { id: "hist-3", licensee: "Kanan Devan", year: "2022-23", claimed: 116.91, approved: 116.91, type: "surplus" },
    { id: "hist-4", licensee: "CSEZA", year: "2023-24", claimed: -3.42, approved: 87.85, type: "reversal" },
    { id: "hist-5", licensee: "Kanan Devan", year: "2021-22", claimed: 13.61, approved: 58.72, type: "overshoot" },
    { id: "hist-6", licensee: "Infoparks", year: "2020-21", claimed: -76.53, approved: -60.80, type: "gap" },
    { id: "hist-7", licensee: "Infoparks", year: "2024-25", claimed: -79.76, approved: -64.72, type: "gap" },
    { id: "hist-8", licensee: "Kanan Devan", year: "2023-24", claimed: -36.91, approved: -36.91, type: "gap" },
    { id: "hist-9", licensee: "Kanan Devan", year: "2024-25", claimed: -3.81, approved: -3.81, type: "gap" },
    { id: "hist-10", licensee: "Kanan Devan", year: "2021-22", claimed: 58.72, approved: 58.72, type: "surplus" },
];

const LICENSEES = ["All", "Infoparks", "Technopark", "Kanan Devan", "CSEZA"];
const YEARS = ["All", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"];
const STATUSES = ["All", "surplus", "gap", "reversal", "overshoot"];

const STATUS_CONFIG: Record<string, { label: string; color: string; badge: string }> = {
    surplus: { label: "SURPLUS ✅", color: "bg-green-50 text-green-800 border-green-200", badge: "text-green-700" },
    gap: { label: "GAP ❌", color: "bg-red-50 text-red-800 border-red-200", badge: "text-red-700" },
    reversal: { label: "REVERSAL ⚠️", color: "bg-amber-50 text-amber-800 border-amber-200", badge: "text-amber-700" },
    overshoot: { label: "OVERSHOOT ⚠️", color: "bg-orange-50 text-orange-800 border-orange-200", badge: "text-orange-700" },
};

// Build chart data: group by licensee, each bar = sum of approved per year
function buildChartData(data: typeof HISTORICAL_DATA) {
    const byYear: Record<string, Record<string, number>> = {};
    data.forEach(d => {
        if (!byYear[d.year]) byYear[d.year] = {};
        byYear[d.year][d.licensee] = (byYear[d.year][d.licensee] || 0) + d.approved;
    });
    return Object.entries(byYear)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([year, vals]) => ({ year, ...vals }));
}

const LICENSEE_COLORS: Record<string, string> = {
    Technopark: "#2C6FAC",
    CSEZA: "#C8960C",
    "Kanan Devan": "#1A7F4B",
    Infoparks: "#C0392B",
};

const ROWS_PER_PAGE = 15;

// CSV export
function exportCSV(data: typeof HISTORICAL_DATA) {
    const header = ["Licensee", "Year", "Claimed (Cr)", "Approved (Cr)", "Status"].join(",");
    const rows = data.map(d =>
        [d.licensee, d.year, d.claimed.toFixed(2), d.approved.toFixed(2), d.type].join(",")
    );
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "KSERC_Historical_Data.csv";
    a.click();
}

export default function HistoryPage() {
    const router = useRouter();

    const [filterLicensee, setFilterLicensee] = useState("All");
    const [filterYear, setFilterYear] = useState("All");
    const [filterStatus, setFilterStatus] = useState("All");
    const [page, setPage] = useState(1);
    const [sortField, setSortField] = useState<"year" | "approved">("year");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

    const filtered = useMemo(() => {
        return HISTORICAL_DATA
            .filter(d => {
                if (filterLicensee !== "All" && d.licensee !== filterLicensee) return false;
                if (filterYear !== "All" && d.year !== filterYear) return false;
                if (filterStatus !== "All" && d.type !== filterStatus) return false;
                return true;
            })
            .sort((a, b) => {
                const mul = sortDir === "asc" ? 1 : -1;
                if (sortField === "year") return a.year.localeCompare(b.year) * mul;
                return (a.approved - b.approved) * mul;
            });
    }, [filterLicensee, filterYear, filterStatus, sortField, sortDir]);

    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    const paged = filtered.slice((page - 1) * ROWS_PER_PAGE, page * ROWS_PER_PAGE);

    const chartData = useMemo(() => buildChartData(filtered), [filtered]);
    const chartLicensees = Array.from(new Set(filtered.map(d => d.licensee)));

    const toggleSort = (field: "year" | "approved") => {
        if (sortField === field) setSortDir(d => d === "asc" ? "desc" : "asc");
        else { setSortField(field); setSortDir("asc"); }
        setPage(1);
    };

    const resetFilters = () => {
        setFilterLicensee("All"); setFilterYear("All"); setFilterStatus("All"); setPage(1);
    };

    const totalSurplus = filtered.filter(d => d.approved > 0).reduce((s, d) => s + d.approved, 0);
    const totalGap = filtered.filter(d => d.approved < 0).reduce((s, d) => s + Math.abs(d.approved), 0);

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto max-w-6xl space-y-6 pt-4 pb-16"
        >
            {/* Breadcrumb */}
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
                <button onClick={() => router.push("/")} className="hover:text-blue transition-colors">Dashboard</button>
                <ChevronRight size={12} />
                <span className="text-navy font-semibold">Historical Data</span>
            </div>

            {/* Header */}
            <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-navy mb-1 leading-none">
                        Historical Truing-Up Data
                    </h1>
                    <p className="text-[14px] text-muted-foreground mt-2">
                        Year-on-year surplus and gap analysis for all distribution licensees.
                    </p>
                </div>
                <Button
                    onClick={() => exportCSV(filtered)}
                    variant="outline"
                    className="gap-2 border-blue/20 text-blue hover:bg-blue-bg shadow-sm"
                >
                    <Download size={15} /> Export Data
                </Button>
            </div>

            {/* Summary stat cards */}
            <div className="grid grid-cols-3 gap-4">
                {[
                    { label: "Total Records", value: filtered.length, sub: "matching filters", color: "border-t-blue", text: "text-navy" },
                    { label: "Cumulative Surplus", value: `₹${totalSurplus.toFixed(2)} Cr`, sub: "over-recovery", color: "border-t-green-500", text: "text-green-700" },
                    { label: "Cumulative Gap", value: `₹${totalGap.toFixed(2)} Cr`, sub: "under-recovery", color: "border-t-red-500", text: "text-red-600" },
                ].map((s, i) => (
                    <Card key={i} className={`border-t-[3px] shadow-sm ${s.color}`}>
                        <CardContent className="p-5">
                            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1">{s.label}</div>
                            <div className={`font-mono text-2xl font-bold ${s.text}`}>{s.value}</div>
                            <div className="text-[10px] text-slate-400 mt-0.5 font-semibold uppercase tracking-wide">{s.sub}</div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Filters */}
            <Card className="shadow-sm border-border">
                <CardHeader className="border-b bg-slate-50/50 py-3 px-5">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-[13px] font-semibold text-navy">
                            <Filter size={14} className="text-blue" /> Filters
                        </div>
                        <button onClick={resetFilters} className="text-[11px] text-muted-foreground hover:text-blue transition-colors">
                            Reset all
                        </button>
                    </div>
                </CardHeader>
                <CardContent className="p-4">
                    <div className="flex flex-wrap gap-4 items-end">
                        <div className="space-y-1.5 min-w-[180px]">
                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Licensee</label>
                            <Select value={filterLicensee} onValueChange={v => { setFilterLicensee(v); setPage(1); }}>
                                <SelectTrigger className="h-9 text-[13px]"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {LICENSEES.map(l => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5 min-w-[150px]">
                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Year</label>
                            <Select value={filterYear} onValueChange={v => { setFilterYear(v); setPage(1); }}>
                                <SelectTrigger className="h-9 text-[13px]"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {YEARS.map(y => <SelectItem key={y} value={y}>{y}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5 min-w-[160px]">
                            <label className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Status</label>
                            <Select value={filterStatus} onValueChange={v => { setFilterStatus(v); setPage(1); }}>
                                <SelectTrigger className="h-9 text-[13px]"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {STATUSES.map(s => <SelectItem key={s} value={s} className="capitalize">{s === "All" ? "All" : STATUS_CONFIG[s]?.label || s}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Table */}
            <Card className="shadow-md border-slate-200 overflow-hidden">
                <CardHeader className="border-b bg-slate-50/50 px-6 py-4">
                    <CardTitle className="text-[15px]">Truing-Up Records</CardTitle>
                    <CardDescription className="text-xs">
                        Showing {paged.length} of {filtered.length} records · Page {page} of {totalPages}
                    </CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="overflow-x-auto">
                        <table className="w-full text-[13.5px]">
                            <thead>
                                <tr className="bg-navy text-white">
                                    <th className="text-left px-6 py-3 font-semibold text-white/90 text-[11px] uppercase tracking-wider">Licensee</th>
                                    <th
                                        className="text-left px-4 py-3 font-semibold text-white/90 text-[11px] uppercase tracking-wider cursor-pointer hover:text-white group"
                                        onClick={() => toggleSort("year")}
                                    >
                                        <span className="flex items-center gap-1">Year <ArrowUpDown size={11} className="opacity-50 group-hover:opacity-100" /></span>
                                    </th>
                                    <th className="text-right px-4 py-3 font-semibold text-white/90 text-[11px] uppercase tracking-wider">Claimed (₹ Cr)</th>
                                    <th
                                        className="text-right px-4 py-3 font-semibold text-white/90 text-[11px] uppercase tracking-wider cursor-pointer hover:text-white group"
                                        onClick={() => toggleSort("approved")}
                                    >
                                        <span className="flex items-center justify-end gap-1">Approved (₹ Cr) <ArrowUpDown size={11} className="opacity-50 group-hover:opacity-100" /></span>
                                    </th>
                                    <th className="text-center px-6 py-3 font-semibold text-white/90 text-[11px] uppercase tracking-wider">Status</th>
                                    <th className="text-center px-4 py-3 font-semibold text-white/90 text-[11px] uppercase tracking-wider">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {paged.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="py-12 text-center text-muted-foreground">
                                            No records match the selected filters.
                                        </td>
                                    </tr>
                                ) : paged.map((row, i) => {
                                    const cfg = STATUS_CONFIG[row.type];
                                    return (
                                        <motion.tr
                                            key={row.id}
                                            initial={{ opacity: 0, x: -8 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.03 }}
                                            className="bg-white hover:bg-slate-50/80 transition-colors"
                                        >
                                            <td className="px-6 py-3.5 font-medium text-navy">{row.licensee}</td>
                                            <td className="px-4 py-3.5 font-mono text-slate-600">{row.year}</td>
                                            <td className="px-4 py-3.5 text-right font-mono text-slate-600">
                                                {row.claimed === 0 ? "—" : (row.claimed > 0 ? "+" : "") + `₹${row.claimed.toFixed(2)}`}
                                            </td>
                                            <td className={`px-4 py-3.5 text-right font-mono font-bold ${row.approved >= 0 ? "text-green-700" : "text-red-600"}`}>
                                                {row.approved >= 0 ? "+" : ""}₹{row.approved.toFixed(2)}
                                            </td>
                                            <td className="px-6 py-3.5 text-center">
                                                <Badge variant="outline" className={`text-[10px] font-bold uppercase tracking-wide px-2.5 py-0.5 ${cfg.color}`}>
                                                    {row.type === "surplus" && <TrendingUp className="inline mr-1 h-3 w-3" />}
                                                    {row.type === "gap" && <TrendingDown className="inline mr-1 h-3 w-3" />}
                                                    {row.type.toUpperCase()}
                                                </Badge>
                                            </td>
                                            <td className="px-4 py-3.5 text-center">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="h-7 text-[11px] text-blue hover:bg-blue-bg gap-1"
                                                    onClick={() => router.push("/")}
                                                >
                                                    <Eye size={12} /> View Order
                                                </Button>
                                            </td>
                                        </motion.tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-between border-t bg-slate-50 px-6 py-3">
                            <span className="text-xs text-muted-foreground">Page {page} of {totalPages}</span>
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" className="h-8 text-xs" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
                                <Button variant="outline" size="sm" className="h-8 text-xs" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
                            </div>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Bar Chart */}
            <Card className="shadow-md border-slate-200">
                <CardHeader className="border-b bg-slate-50/50 px-6 py-4">
                    <CardTitle className="text-[15px]">Year-on-Year Surplus / Gap by Licensee</CardTitle>
                    <CardDescription className="text-xs">Positive = surplus (over-recovery), negative = gap (under-recovery). Values in ₹ Crore.</CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                    <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                            <XAxis dataKey="year" tick={{ fontSize: 12, fill: "#5A6A7A" }} axisLine={false} tickLine={false} />
                            <YAxis
                                tick={{ fontSize: 11, fill: "#9AAABB" }}
                                axisLine={false}
                                tickLine={false}
                                tickFormatter={(v) => `₹${v}`}
                                width={60}
                            />
                            <Tooltip
                                contentStyle={{ borderRadius: 8, border: '1px solid #DEE2E8', fontSize: 12, boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                                formatter={(v: any) => [`₹${Number(v).toFixed(2)} Cr`, ""]}
                            />
                            <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, paddingTop: 16 }} />
                            <ReferenceLine y={0} stroke="#1C2B3A" strokeWidth={1.5} />
                            {chartLicensees.map((lic, i) => (
                                <Bar
                                    key={lic}
                                    dataKey={lic}
                                    fill={LICENSEE_COLORS[lic] || `hsl(${i * 60}, 55%, 45%)`}
                                    radius={[4, 4, 0, 0]}
                                    maxBarSize={38}
                                >
                                    {chartData.map((entry: any, idx: number) => (
                                        <Cell
                                            key={idx}
                                            fill={entry[lic] < 0
                                                ? `${LICENSEE_COLORS[lic] || "#C0392B"}CC`
                                                : LICENSEE_COLORS[lic] || `hsl(${i * 60}, 55%, 45%)`
                                            }
                                        />
                                    ))}
                                </Bar>
                            ))}
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </motion.div>
    );
}
