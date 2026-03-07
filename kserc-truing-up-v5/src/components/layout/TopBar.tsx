"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

export function TopBar() {
    const router = useRouter();

    const doLogout = () => {
        // Basic logout logic for now
        router.push("/login");
    };

    return (
        <header className="fixed inset-x-0 top-0 z-[300] flex h-[60px] items-center gap-3 border-b-2 border-gold bg-navy px-6">
            <div className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-full bg-gold font-serif text-[11px] font-bold text-navy">
                KSERC
            </div>
            <div className="flex flex-col leading-[1.2]">
                <b className="font-serif text-[14.5px] font-semibold text-white">
                    Kerala State Electricity Regulatory Commission
                </b>
                <small className="text-[10px] uppercase tracking-[0.9px] text-gold-light">
                    AI Truing-Up Analytical Tool
                </small>
            </div>
            <div className="h-[26px] w-[1px] bg-white/10 mx-2" />
            <span className="text-[11px] tracking-[0.4px] text-white/40">
                Work Order KSERC/CSO/03-05 &nbsp;·&nbsp; RIET Thiruvananthapuram
            </span>

            <div className="ml-auto flex items-center gap-4">
                <div className="flex items-center gap-2 text-[13px] text-white/75">
                    <div className="flex h-[28px] w-[28px] items-center justify-center rounded-full border border-white/20 bg-navy-muted text-[10px] font-bold text-white/80">
                        PS
                    </div>
                    <span>KSERC Staff</span>
                </div>
                <button
                    onClick={doLogout}
                    className="flex items-center gap-2 rounded border border-white/10 px-2.5 py-1 text-[11.5px] text-white/40 transition-colors hover:border-white/30 hover:text-white"
                >
                    <LogOut size={14} />
                    Logout
                </button>
            </div>
        </header>
    );
}
