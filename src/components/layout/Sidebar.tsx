"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UploadCloud, BarChart2, FileText, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

export function Sidebar() {
    const pathname = usePathname();

    const isActive = (path: string) => {
        if (path === "/" && pathname === "/") return true;
        if (path !== "/" && pathname.startsWith(path)) return true;
        return false;
    };

    const navItemClass = (path: string) =>
        cn(
            "flex items-center gap-2 px-4 py-2 text-[13px] font-medium transition-colors border-l-2",
            isActive(path)
                ? "border-gold bg-blue/20 text-white"
                : "border-transparent text-white/50 hover:border-gold/30 hover:bg-white/5 hover:text-white/80"
        );

    return (
        <nav className="fixed bottom-0 left-0 top-[60px] z-[100] flex w-[216px] flex-col overflow-y-auto bg-navy-dark">
            <div className="pb-1.5 pt-4">
                <div className="px-4 pb-[7px] text-[9.5px] font-bold uppercase tracking-[1.2px] text-white/20">
                    Main
                </div>
                <Link href="/" className={navItemClass("/")}>
                    <UploadCloud className={cn("h-[15px] w-[15px] shrink-0", isActive("/") ? "opacity-100" : "opacity-70")} />
                    Upload & Analyse
                </Link>
                <Link href="/results" className={navItemClass("/results")}>
                    <BarChart2 className={cn("h-[15px] w-[15px] shrink-0", isActive("/results") ? "opacity-100" : "opacity-70")} />
                    Analysis Results
                </Link>
                <Link href="/report" className={navItemClass("/report")}>
                    <FileText className={cn("h-[15px] w-[15px] shrink-0", isActive("/report") ? "opacity-100" : "opacity-70")} />
                    Generate Report
                </Link>
            </div>

            <div className="pb-1.5 pt-4">
                <div className="px-4 pb-[7px] text-[9.5px] font-bold uppercase tracking-[1.2px] text-white/20">
                    Reference
                </div>
                <Link href="/rules" className={navItemClass("/rules")}>
                    <BookOpen className={cn("h-[15px] w-[15px] shrink-0", isActive("/rules") ? "opacity-100" : "opacity-70")} />
                    Regulatory Rules
                </Link>
            </div>

            <div className="mt-auto border-t border-white/5 px-4 py-[13px] text-[9.5px] leading-[1.8] text-white/20">
                v0.1 · RIET ISR Project<br />
                AI: Groq (Llama-3.3-70b)<br />
                Work Order: KSERC/CSO/03-05<br />
                All data from uploaded docs
            </div>
        </nav>
    );
}
