import { useEffect, useState } from 'react'

const STEPS = [
    'Extracting financial tables from PDF...',
    'Running compliance audit against KSERC Regulations...',
    'Generating detailed justifications...',
    'Preparing PDF order document...',
]

export default function LoadingScreen() {
    const [activeStep, setActiveStep] = useState(0)

    useEffect(() => {
        const timers = STEPS.map((_, i) =>
            setTimeout(() => setActiveStep(i), i * 3000 + 2000)
        )
        return () => timers.forEach(clearTimeout)
    }, [])

    return (
        <section className="animate-fade-in-up flex justify-center py-16">
            <div className="text-center max-w-lg bg-kserc-surface/60 backdrop-blur-2xl border border-white/10 rounded-3xl p-10 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-1/4 right-1/4 h-[2px] bg-gradient-to-r from-transparent via-kserc-blue to-transparent opacity-50 shadow-[0_0_10px_var(--color-kserc-blue)]" />

                {/* Pulse animation */}
                <div className="relative w-32 h-32 mx-auto mb-10">
                    <div className="absolute inset-0 rounded-full bg-kserc-blue/10 animate-pulse-ring" />
                    <div className="absolute inset-3 rounded-full bg-kserc-blue/15 animate-pulse-ring" style={{ animationDelay: '0.5s' }} />
                    <div className="absolute inset-6 rounded-full bg-kserc-blue/20 animate-pulse-ring" style={{ animationDelay: '1s' }} />
                    <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-5xl drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]">⚡</span>
                    </div>
                </div>

                <h2 className="text-2xl font-bold text-white mb-8 tracking-wide drop-shadow-md">Analyzing Petition</h2>

                <div className="space-y-4 text-left relative z-10">
                    {STEPS.map((step, i) => (
                        <div
                            key={i}
                            className={`flex items-center gap-4 px-6 py-4 rounded-xl transition-all duration-500 border border-transparent ${i < activeStep
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                                : i === activeStep
                                    ? 'bg-kserc-blue/10 text-white border-kserc-blue/30 shadow-[0_0_15px_rgba(59,130,246,0.15)] animate-[pulse_2s_ease-in-out_infinite]'
                                    : 'bg-black/20 text-white/40 border-white/5'
                                }`}
                        >
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all ${i < activeStep
                                ? 'bg-emerald-500 border-emerald-500 text-white shadow-[0_0_10px_rgba(16,185,129,0.5)]'
                                : i === activeStep
                                    ? 'border-kserc-blue text-kserc-blue shadow-[0_0_10px_rgba(59,130,246,0.3)] bg-kserc-blue/10'
                                    : 'border-white/20 text-white/30 bg-black/40'
                                }`}>
                                {i < activeStep ? '✔' : i + 1}
                            </div>
                            <span className="text-sm font-semibold tracking-wide">{step}</span>
                        </div>
                    ))}
                </div>

                <p className="mt-10 text-xs text-white/40 font-mono uppercase tracking-widest">
                    This process may take 2-5 minutes depending on the document complexity.
                </p>
            </div>
        </section>
    )
}
