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
            <div className="text-center max-w-lg">
                {/* Pulse animation */}
                <div className="relative w-32 h-32 mx-auto mb-10">
                    <div className="absolute inset-0 rounded-full bg-kserc-gold/10 animate-pulse-ring" />
                    <div className="absolute inset-3 rounded-full bg-kserc-gold/15 animate-pulse-ring" style={{ animationDelay: '0.5s' }} />
                    <div className="absolute inset-6 rounded-full bg-kserc-gold/20 animate-pulse-ring" style={{ animationDelay: '1s' }} />
                    <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-5xl">⚡</span>
                    </div>
                </div>

                <h2 className="text-2xl font-bold text-kserc-navy mb-8">Analyzing Petition</h2>

                <div className="space-y-4 text-left">
                    {STEPS.map((step, i) => (
                        <div
                            key={i}
                            className={`flex items-center gap-3 px-5 py-3 rounded-lg transition-all duration-500 ${i < activeStep
                                    ? 'bg-kserc-green/10 text-kserc-green'
                                    : i === activeStep
                                        ? 'bg-kserc-navy/5 text-kserc-navy animate-shimmer'
                                        : 'text-kserc-text-muted/50'
                                }`}
                        >
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${i < activeStep
                                    ? 'bg-kserc-green border-kserc-green text-white'
                                    : i === activeStep
                                        ? 'border-kserc-navy text-kserc-navy'
                                        : 'border-gray-300 text-gray-300'
                                }`}>
                                {i < activeStep ? '✓' : i + 1}
                            </div>
                            <span className="text-sm font-medium">{step}</span>
                        </div>
                    ))}
                </div>

                <p className="mt-8 text-xs text-kserc-text-muted">
                    This process may take 2-5 minutes depending on the document complexity.
                </p>
            </div>
        </section>
    )
}
