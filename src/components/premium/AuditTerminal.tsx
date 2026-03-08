'use client';

import { useState, useEffect, useRef } from 'react';
import { Terminal, Cpu, CheckCircle, AlertCircle, Search, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface LogEntry {
    id: string;
    timestamp: string;
    type: 'info' | 'success' | 'warning' | 'error' | 'ai';
    message: string;
    node?: string;
}

interface AuditTerminalProps {
    logs: LogEntry[];
    isProcessing: boolean;
    currentStep?: string;
}

export default function AuditTerminal({ logs, isProcessing, currentStep }: AuditTerminalProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="bg-[#0A1628] rounded-2xl border border-slate-700 shadow-2xl overflow-hidden font-mono text-[13px] h-[400px] flex flex-col">
            {/* Header */}
            <div className="px-5 py-3 border-b border-slate-700 bg-[#0F1E35] flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                        <div className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
                        <div className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
                        <div className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
                    </div>
                    <div className="h-4 w-[1px] bg-slate-700 mx-2" />
                    <div className="flex items-center gap-2 text-slate-400 text-[10px] font-black uppercase tracking-widest">
                        <Terminal size={12} className="text-cyan-400" />
                        Live AI Audit Telemetry
                    </div>
                </div>
                {isProcessing && (
                    <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full bg-cyan-500 animate-pulse shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
                        <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-tighter">Processing...</span>
                    </div>
                )}
            </div>

            {/* Content */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-5 space-y-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent"
            >
                <AnimatePresence initial={false}>
                    {logs.map((log) => (
                        <motion.div
                            key={log.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            className="group flex gap-3"
                        >
                            <span className="text-slate-600 shrink-0 select-none">[{log.timestamp}]</span>
                            <div className="flex-1 flex gap-2">
                                <LogIcon type={log.type} />
                                <div className="flex-1">
                                    {log.node && (
                                        <span className="text-kserc-gold font-bold mr-2 text-[11px] uppercase">[{log.node}]</span>
                                    )}
                                    <span className={getMessageColor(log.type)}>{log.message}</span>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
                {isProcessing && (
                    <motion.div
                        animate={{ opacity: [0.4, 1, 0.4] }}
                        transition={{ repeat: Infinity, duration: 1.5 }}
                        className="text-cyan-400/50"
                    >
                        ▌
                    </motion.div>
                )}
            </div>

            {/* Footer / Status bar */}
            <div className="px-5 py-2 border-t border-slate-700 bg-[#071120] text-[10px] text-slate-500 flex justify-between items-center">
                <div className="flex gap-4 uppercase font-bold tracking-tight">
                    <span>ENV: PRODUCTION_v6</span>
                    <span>ENGINE: Gemini-1.5-Pro</span>
                    <span>LOC: TRIVANDRUM_HQ</span>
                </div>
                <div className="text-cyan-400/80 font-bold">
                    {currentStep || 'IDLE'}
                </div>
            </div>
        </div>
    );
}

function LogIcon({ type }: { type: LogEntry['type'] }) {
    switch (type) {
        case 'success': return <CheckCircle size={14} className="text-emerald-500 mt-0.5" />;
        case 'warning': return <AlertCircle size={14} className="text-amber-500 mt-0.5" />;
        case 'error': return <AlertCircle size={14} className="text-red-500 mt-0.5" />;
        case 'ai': return <Cpu size={14} className="text-cyan-400 mt-0.5 shadow-[0_0_8px_rgba(6,182,212,0.4)]" />;
        default: return <Info size={14} className="text-slate-400 mt-0.5" />;
    }
}

function getMessageColor(type: LogEntry['type']) {
    switch (type) {
        case 'success': return 'text-emerald-400';
        case 'warning': return 'text-amber-400';
        case 'error': return 'text-red-400';
        case 'ai': return 'text-cyan-300';
        default: return 'text-slate-300';
    }
}
