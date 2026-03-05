export default function Header() {
    const today = new Date().toLocaleDateString('en-IN', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    })

    return (
        <header className="bg-gradient-to-r from-kserc-navy via-kserc-navy-light to-kserc-navy relative overflow-hidden">
            {/* Subtle pattern overlay */}
            <div className="absolute inset-0 opacity-5"
                style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.03) 10px, rgba(255,255,255,0.03) 20px)' }}
            />

            <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-5">
                        {/* Emblem */}
                        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-kserc-gold to-kserc-gold-dark flex items-center justify-center shadow-lg shadow-kserc-gold/20 border-2 border-kserc-gold-light/30">
                            <span className="text-3xl">⚡</span>
                        </div>
                        <div>
                            <h1 className="text-white text-xl sm:text-2xl font-bold tracking-tight leading-tight">
                                Kerala State Electricity Regulatory Commission
                            </h1>
                            <p className="text-kserc-gold/80 text-sm mt-0.5 font-medium">
                                കേരള സംസ്ഥാന വൈദ്യുതി റെഗുലേറ്ററി കമ്മീഷൻ
                            </p>
                            <p className="text-white/50 text-xs mt-1 tracking-wider uppercase">
                                Automated Tariff Truing Up Analysis System
                            </p>
                        </div>
                    </div>

                    <div className="hidden md:flex flex-col items-end gap-2">
                        <span className="inline-flex items-center px-3 py-1 rounded text-[10px] font-bold tracking-widest uppercase bg-kserc-red/20 text-red-300 border border-red-400/30">
                            Restricted
                        </span>
                        <span className="text-white/40 text-xs">{today}</span>
                    </div>
                </div>
            </div>

            {/* Gold accent line */}
            <div className="h-1 bg-gradient-to-r from-kserc-gold-dark via-kserc-gold to-kserc-gold-dark" />
        </header>
    )
}
