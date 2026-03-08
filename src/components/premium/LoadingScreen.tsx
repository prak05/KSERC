'use client';

import { Shield, Cpu, Binary, Search, CheckCircle } from 'lucide-react';

export default function PremiumLoadingScreen() {
    return (
        <div className="max-w-4xl mx-auto py-20 animate-fade-in-up">
            <div className="flex flex-col items-center text-center space-y-12">
                <div className="relative">
                    {/* Animated rings */}
                    <div className="absolute inset-0 -m-8 border-4 border-kserc-gold/20 rounded-full animate-pulse-ring" />
                    <div className="absolute inset-0 -m-16 border-2 border-kserc-blue/10 rounded-full animate-pulse-ring delay-700" />

                    <div className="h-32 w-32 rounded-3xl bg-kserc-navy flex items-center justify-center text-white shadow-2xl shadow-kserc-navy/40 relative z-10 overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent animate-shimmer" />
                        <Shield size={48} className="text-kserc-gold" />
                    </div>
                </div>

                <div className="space-y-4">
                    <h2 className="text-3xl font-black text-kserc-navy tracking-tight">Deploying ARA Multi-Agent Cycle</h2>
                    <p className="text-kserc-text-muted max-w-md mx-auto font-medium">
                        **The Clerk** is extracting data, while the **Forensic Auditor** validates mathematical precision against RIET regulatory standards.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mt-12">
                    <LoadingStep icon={<Cpu size={20} />} label="The Clerk" description="Mapping PDF tables to Regulatory Schema" active />
                    <LoadingStep icon={<Binary size={20} />} label="Forensic Auditor" description="Verifying values with 99.732% math" />
                    <LoadingStep icon={<Search size={20} />} label="The Legal Brain" description="Synthesizing RAG context & precedents" />
                </div>

                <div className="w-full max-w-lg bg-kserc-surface h-3 rounded-full overflow-hidden border border-kserc-border relative">
                    <div className="h-full bg-gradient-to-r from-kserc-navy via-kserc-blue to-kserc-gold w-[65%] animate-pulse rounded-full" />
                </div>

                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-kserc-gold">System integrity validated · Initializing analysis</p>
            </div>
        </div>
    );
}

function LoadingStep({ icon, label, description, active }: { icon: React.ReactNode; label: string; description: string; active?: boolean }) {
    return (
        <div className={`p-6 rounded-2xl border transition-all duration-500 text-left ${active ? 'bg-white border-kserc-gold shadow-lg ring-4 ring-kserc-gold/5 scale-105' : 'bg-white/50 border-kserc-border opacity-50'}`}>
            <div className={`h-10 w-10 rounded-xl flex items-center justify-center mb-4 ${active ? 'bg-kserc-gold text-kserc-navy' : 'bg-kserc-surface text-kserc-text-muted'}`}>
                {icon}
            </div>
            <h4 className={`font-black text-sm mb-1 ${active ? 'text-kserc-navy' : 'text-kserc-text-muted'}`}>{label}</h4>
            <p className="text-[11px] font-medium text-kserc-text-muted leading-relaxed">{description}</p>
        </div>
    );
}
