export default function Footer() {
    return (
        <footer className="bg-black/40 backdrop-blur-xl border-t border-white/10 text-white/50 mt-auto relative z-20">
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-kserc-blue/30 to-transparent" />
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                    <div>
                        <p className="text-white/80 font-bold text-sm tracking-wide">Kerala State Electricity Regulatory Commission</p>
                        <p className="text-xs mt-1 text-white/40">KPFC Bhavanam, C.V. Raman Pillai Road, Vellayambalam, Thiruvananthapuram - 695010</p>
                    </div>
                    <div className="text-left md:text-right text-xs">
                        <p className="font-semibold text-white/60">Developed under the directives of KSERC</p>
                        <p className="text-white/30 mt-1">This is an automated analysis tool. Final orders are subject to Commission's approval.</p>
                    </div>
                </div>
            </div>
        </footer>
    )
}
