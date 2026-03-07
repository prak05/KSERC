export default function Navigation({ currentView, onNavigate, hasResults }) {
    return (
        <nav className="bg-white border-b border-kserc-border shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => onNavigate('upload')}
                        className={`px-5 py-3.5 text-sm font-medium border-b-2 transition-all duration-200 ${currentView === 'upload'
                                ? 'border-kserc-navy text-kserc-navy bg-kserc-navy/5'
                                : 'border-transparent text-kserc-text-muted hover:text-kserc-navy hover:border-kserc-border'
                            }`}
                    >
                        📤 Submit Petition
                    </button>

                    {hasResults && (
                        <button
                            onClick={() => onNavigate('results')}
                            className={`px-5 py-3.5 text-sm font-medium border-b-2 transition-all duration-200 ${currentView === 'results'
                                    ? 'border-kserc-navy text-kserc-navy bg-kserc-navy/5'
                                    : 'border-transparent text-kserc-text-muted hover:text-kserc-navy hover:border-kserc-border'
                                }`}
                        >
                            📊 Analysis Results
                        </button>
                    )}
                </div>
            </div>
        </nav>
    )
}
