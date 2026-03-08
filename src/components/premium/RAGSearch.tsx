'use client';

import { useState } from 'react';
import { Search, Book, Gavel, ArrowRight, Loader2, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from "@/components/ui/badge";

interface SearchResult {
    id: string;
    source: 'regulation' | 'precedent';
    title: string;
    content: string;
    relevance: number;
}

export default function RAGSearch() {
    const [query, setQuery] = useState('');
    const [isSearching, setIsSearching] = useState(false);
    const [results, setResults] = useState<SearchResult[]>([]);
    const [activeTab, setActiveTab] = useState<'all' | 'regulations' | 'precedents'>('all');

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setIsSearching(true);
        // Simulate RAG Search
        setTimeout(() => {
            setResults([
                {
                    id: '1',
                    source: 'regulation',
                    title: 'KSERC MYT Regulation 2021',
                    content: 'Regulation 27: Depreciation - (1) For the purpose of tariff, depreciation shall be computed in the following manner, namely: (a) The value base for the purpose of depreciation shall be the capital cost of the asset as admitted by the Commission...',
                    relevance: 98
                },
                {
                    id: '2',
                    source: 'precedent',
                    title: 'Truing up of Technopark FY 2021-22',
                    content: 'In the matter of R&M expenses, the Commission observed that the licensee has incurred expenditure higher than the norms. However, considering the unique nature of Technocity campus, a one-time relaxation was granted...',
                    relevance: 85
                }
            ]);
            setIsSearching(false);
        }, 1500);
    };

    return (
        <div className="bg-white rounded-3xl border border-kserc-border shadow-xl overflow-hidden flex flex-col h-[600px]">
            {/* Header */}
            <div className="p-8 bg-gradient-to-br from-kserc-navy to-kserc-blue text-white">
                <div className="flex items-center gap-3 mb-4">
                    <div className="h-10 w-10 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center">
                        <Sparkles size={20} className="text-kserc-gold" />
                    </div>
                    <div>
                        <h2 className="text-xl font-black tracking-tight">Interactive RAG Intelligence</h2>
                        <p className="text-xs text-white/60 font-medium">Search the KSERC Regulatory & Precedent Database</p>
                    </div>
                </div>

                <form onSubmit={handleSearch} className="relative">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search regulations, precedents, or audit rules..."
                        className="w-full bg-white/10 border border-white/20 rounded-2xl py-4 pl-12 pr-4 text-sm placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-kserc-gold/50 transition-all backdrop-blur-sm italic"
                    />
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" size={20} />
                    <button
                        type="submit"
                        disabled={isSearching}
                        className="absolute right-2 top-1/2 -translate-y-1/2 h-10 px-6 rounded-xl bg-kserc-gold text-kserc-navy font-black text-[11px] uppercase tracking-widest hover:bg-white transition-all shadow-lg active:scale-95 disabled:opacity-50"
                    >
                        {isSearching ? <Loader2 size={16} className="animate-spin" /> : 'Search'}
                    </button>
                </form>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-kserc-border px-8">
                {(['all', 'regulations', 'precedents'] as const).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`px-4 py-4 text-[10px] font-black uppercase tracking-widest border-b-2 transition-all ${activeTab === tab ? 'border-kserc-navy text-kserc-navy' : 'border-transparent text-kserc-text-muted hover:text-kserc-navy'}`}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-kserc-surface/30">
                <AnimatePresence mode="wait">
                    {isSearching ? (
                        <motion.div
                            key="searching"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center h-full space-y-4 text-kserc-text-muted"
                        >
                            <div className="relative">
                                <div className="h-12 w-12 rounded-full border-4 border-kserc-navy/10 border-t-kserc-gold animate-spin" />
                            </div>
                            <p className="text-xs font-bold uppercase tracking-widest">Querying Vector Store...</p>
                        </motion.div>
                    ) : results.length > 0 ? (
                        <motion.div
                            key="results"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="space-y-4"
                        >
                            {results.filter(r => activeTab === 'all' || r.source + 's' === activeTab).map((result) => (
                                <div key={result.id} className="bg-white p-6 rounded-2xl border border-kserc-border shadow-sm hover:shadow-md transition-all group">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            {result.source === 'regulation' ? <Book size={14} className="text-kserc-blue" /> : <Gavel size={14} className="text-kserc-navy" />}
                                            <span className="text-[10px] font-black uppercase tracking-widest text-kserc-text-muted">{result.source}</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <div className="h-1 w-12 bg-gray-100 rounded-full overflow-hidden">
                                                <div className="h-full bg-kserc-green" style={{ width: `${result.relevance}%` }} />
                                            </div>
                                            <span className="text-[10px] font-black text-kserc-green">{result.relevance}% Match</span>
                                        </div>
                                    </div>
                                    <h3 className="font-black text-kserc-navy mb-2 group-hover:text-kserc-blue transition-colors underline decoration-kserc-gold decoration-2 underline-offset-4">{result.title}</h3>
                                    <p className="text-sm text-kserc-text leading-relaxed font-medium line-clamp-3 italic">
                                        "{result.content}"
                                    </p>
                                    <div className="mt-4 pt-4 border-t border-kserc-border flex justify-end">
                                        <button className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-tighter text-kserc-navy hover:text-kserc-gold transition-colors">
                                            View Full Context <ArrowRight size={12} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </motion.div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                            <div className="h-16 w-16 rounded-full bg-kserc-navy/5 flex items-center justify-center text-kserc-navy/20">
                                <Search size={32} />
                            </div>
                            <div>
                                <h4 className="font-black text-kserc-navy">Intelligent Knowledge Discovery</h4>
                                <p className="text-xs text-kserc-text-muted mt-1 max-w-[240px] font-medium leading-relaxed">Enter a natural language query to find relevant KSERC regulations and precedents.</p>
                            </div>
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
