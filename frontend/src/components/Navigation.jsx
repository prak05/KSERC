export default function Navigation({ currentView, onNavigate, hasResults }) {
    return (
        <nav className="sticky top-4 z-40 mt-4 mb-2 flex justify-center w-full pointer-events-none">
            <div className="bg-kserc-surface/60 backdrop-blur-xl border border-kserc-border shadow-lg shadow-black/20 rounded-full px-2 py-1.5 pointer-events-auto flex items-center justify-center gap-2 transition-all duration-300">
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => onNavigate('upload')}
                        className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all duration-300 relative overflow-hidden group ${currentView === 'upload'
                            ? 'text-white bg-white/10 shadow-[inset_0_1px_rgba(255,255,255,0.1)] ring-1 ring-white/20'
                            : 'text-kserc-text-muted hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <span className="relative z-10 flex items-center gap-2">
                            <span>📤</span> Submit Petition
                        </span>
                        {currentView === 'upload' && (
                            <span className="absolute bottom-0 left-1/4 right-1/4 h-[2px] bg-kserc-blue shadow-[0_0_8px_var(--color-kserc-blue)] rounded-t-full" />
                        )}
                    </button>

                    {hasResults && (
                        <button
                            onClick={() => onNavigate('results')}
                            className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all duration-300 relative overflow-hidden group ${currentView === 'results'
                                ? 'text-white bg-white/10 shadow-[inset_0_1px_rgba(255,255,255,0.1)] ring-1 ring-white/20'
                                : 'text-kserc-text-muted hover:text-white hover:bg-white/5'
                                }`}
                        >
                            <span className="relative z-10 flex items-center gap-2">
                                <span>📊</span> Analysis Results
                            </span>
                            {currentView === 'results' && (
                                <span className="absolute bottom-0 left-1/4 right-1/4 h-[2px] bg-kserc-gold shadow-[0_0_8px_var(--color-kserc-gold)] rounded-t-full" />
                            )}
                        </button>
                    )}

                    <button
                        onClick={() => onNavigate('reference')}
                        className={`px-5 py-2.5 rounded-full text-sm font-medium transition-all duration-300 relative overflow-hidden group ${currentView === 'reference'
                            ? 'text-white bg-white/10 shadow-[inset_0_1px_rgba(255,255,255,0.1)] ring-1 ring-white/20'
                            : 'text-kserc-text-muted hover:text-white hover:bg-white/5'
                            }`}
                    >
                        <span className="relative z-10 flex items-center gap-2">
                            <span>🗄️</span> Reference Data
                        </span>
                        {currentView === 'reference' && (
                            <span className="absolute bottom-0 left-1/4 right-1/4 h-[2px] bg-kserc-green shadow-[0_0_8px_var(--color-kserc-green)] rounded-t-full" />
                        )}
                    </button>
                </div>
            </div>
        </nav>
    )
}
