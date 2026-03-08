import Link from 'next/link';

export default function Header() {
    return (
        <header className="bg-white border-b border-kserc-border sticky top-0 z-50 backdrop-blur-md bg-white/90">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-20">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="flex items-center gap-3 group">
                            <div className="h-12 w-12 rounded-xl bg-kserc-navy flex items-center justify-center text-white font-serif text-2xl font-bold border-2 border-kserc-gold shadow-lg group-hover:scale-105 transition-transform duration-300">
                                K
                            </div>
                            <div>
                                <h1 className="text-xl font-bold bg-gradient-to-r from-kserc-navy to-kserc-blue bg-clip-text text-transparent tracking-tight leading-none">
                                    KSERC <span className="text-kserc-gold">Truing-Up</span>
                                </h1>
                                <p className="text-[10px] text-kserc-text-muted uppercase tracking-[0.2em] font-bold mt-1.5 font-sans">
                                    Kerala State Electricity Regulatory Commission
                                </p>
                            </div>
                        </Link>
                    </div>

                    <nav className="hidden lg:flex items-center gap-8">
                        <Link href="/" className="text-sm font-bold text-kserc-navy border-b-2 border-kserc-gold pb-1 transition-all">
                            Analysis Dashboard
                        </Link>
                        <Link href="#" className="text-sm font-medium text-kserc-text-muted hover:text-kserc-navy transition-colors">
                            Regulations
                        </Link>
                        <Link href="#" className="text-sm font-medium text-kserc-text-muted hover:text-kserc-navy transition-colors">
                            Precedents
                        </Link>
                    </nav>

                    <div className="flex items-center gap-3">
                        <div className="hidden sm:flex flex-col items-end mr-2">
                            <span className="text-[10px] font-bold text-kserc-green uppercase">Live Analytics Status</span>
                            <span className="text-[11px] text-kserc-text-muted">v6.0.0 Premium Early Access</span>
                        </div>
                        <div className="h-2 w-2 rounded-full bg-kserc-green animate-pulse" />
                    </div>
                </div>
            </div>
        </header>
    );
}
