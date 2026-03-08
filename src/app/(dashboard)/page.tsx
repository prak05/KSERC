'use client';

import { useState, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import PremiumUploadForm from '@/components/premium/PremiumUploadForm';
import PremiumLoadingScreen from '@/components/premium/LoadingScreen';
import PremiumReviewModal from '@/components/premium/ReviewModal';
import ResultsDashboard from '@/components/premium/ResultsDashboard';
import AuditTerminal from '@/components/premium/AuditTerminal';
import RAGSearch from '@/components/premium/RAGSearch';
import { AlertCircle, Terminal as TerminalIcon, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

type AppState = 'IDLE' | 'LOADING' | 'REVIEW' | 'SUCCESS' | 'ERROR';

const LICENSEES = ["Technopark", "Infopark", "CSEZA", "KDHP"];
const YEARS = ["2023-24", "2022-23", "2021-22", "2020-21"];

export default function PremiumDashboardV6() {
    const [state, setState] = useState<AppState>('IDLE');
    const [analysisId, setAnalysisId] = useState<string | null>(null);
    const [reviewSummary, setReviewSummary] = useState<any>(null);
    const [results, setResults] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [isSubmittingReview, setIsSubmittingReview] = useState(false);
    const [auditLogs, setAuditLogs] = useState<any[]>([]);
    const [currentStep, setCurrentStep] = useState<string>('');

    const pollRef = useRef<NodeJS.Timeout | null>(null);

    const cleanupPoll = () => {
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
    };

    useEffect(() => cleanupPoll, []);

    const startAnalysis = async (formData: FormData) => {
        setState('LOADING');
        setError(null);
        try {
            const res = await fetch('/api/analyse', { method: 'POST', body: formData });
            if (!res.ok) throw new Error('Failed to initiate analysis pipeline');
            const { analysis_id } = await res.json();
            setAnalysisId(analysis_id);
            startPolling(analysis_id);
        } catch (err: any) {
            setError(err.message);
            setState('ERROR');
        }
    };

    const startPolling = (id: string) => {
        cleanupPoll();
        pollRef.current = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${id}`, { cache: 'no-store' });
                if (!res.ok) return;
                const data = await res.json();

                if (data.status !== 'IDLE') {
                    const timestamp = new Date().toLocaleTimeString();
                    const newLog = {
                        id: Math.random().toString(36).substr(2, 9),
                        timestamp,
                        type: data.status === 'FAILED' ? 'error' : 'ai',
                        message: data.status === 'AWAITING_REVIEW' ? 'Pipeline paused at HITL gate' : 'Processing analysis node...',
                        node: data.status
                    };
                    setAuditLogs(prev => [...prev.slice(-49), newLog]);
                    setCurrentStep(data.status);
                }

                if (data.status === 'AWAITING_REVIEW') {
                    cleanupPoll();
                    setReviewSummary(data.review_summary);
                    setState('REVIEW');
                } else if (data.status === 'COMPLETED') {
                    cleanupPoll();
                    setResults(data.result);
                    setState('SUCCESS');
                } else if (data.status === 'FAILED') {
                    cleanupPoll();
                    setError(data.result?.error || 'Analysis pipeline failure');
                    setState('ERROR');
                }
            } catch (e) {
                // Continue polling on network hiccups
            }
        }, 3000);
    };

    const handleReview = async (approve: boolean, overrideText?: string) => {
        if (!analysisId) return;
        setIsSubmittingReview(true);
        try {
            const response = approve ? "Approve" : (overrideText || "Override");
            const res = await fetch('/api/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ analysis_id: analysisId, response }),
            });
            if (!res.ok) throw new Error('Review submission failed');

            setState('LOADING');
            startPolling(analysisId);
        } catch (err: any) {
            setError(err.message);
            setState('ERROR');
        } finally {
            setIsSubmittingReview(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <AnimatePresence mode="wait">
                {state === 'IDLE' && (
                    <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                        <PremiumUploadForm licensees={LICENSEES} financialYears={YEARS} onSubmit={startAnalysis} />
                    </motion.div>
                )}

                {state === 'LOADING' && (
                    <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                        <PremiumLoadingScreen />
                    </motion.div>
                )}

                {state === 'REVIEW' && reviewSummary && (
                    <motion.div key="review" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                        <PremiumReviewModal
                            summary={reviewSummary}
                            onReviewSubmit={handleReview}
                            isSubmitting={isSubmittingReview}
                        />
                    </motion.div>
                )}

                {state === 'SUCCESS' && results && (
                    <motion.div key="success" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-12">
                        {/* Masterpiece Dashboard Section */}
                        <ResultsDashboard data={results} onNewAnalysis={() => { setState('IDLE'); setAuditLogs([]); }} />

                        {/* Intelligence Section */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-12">
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 px-2 text-kserc-navy">
                                    <TerminalIcon size={18} />
                                    <h3 className="font-black text-xs uppercase tracking-widest">Audit Telemetry History</h3>
                                </div>
                                <AuditTerminal logs={auditLogs} isProcessing={false} currentStep="COMPLETED" />
                            </div>
                            <div className="space-y-4">
                                <div className="flex items-center gap-2 px-2 text-kserc-navy">
                                    <Sparkles size={18} />
                                    <h3 className="font-black text-xs uppercase tracking-widest">Regulatory Intelligence (RAG)</h3>
                                </div>
                                <RAGSearch />
                            </div>
                        </div>
                    </motion.div>
                )}

                {state === 'ERROR' && (
                    <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-center py-20 space-y-6">
                        <div className="h-20 w-20 rounded-full bg-kserc-red/10 flex items-center justify-center text-kserc-red mx-auto">
                            <AlertCircle size={40} />
                        </div>
                        <div className="space-y-2">
                            <h2 className="text-2xl font-black text-kserc-navy tracking-tight">Pipeline Exception</h2>
                            <p className="text-kserc-text-muted font-medium max-w-md mx-auto">{error}</p>
                        </div>
                        <Button onClick={() => setState('IDLE')} variant="outline" className="rounded-xl border-kserc-navy text-kserc-navy px-8">
                            Return to Dashboard
                        </Button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
