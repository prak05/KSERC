export default function Footer() {
    return (
        <footer className="bg-kserc-navy text-white/60 mt-auto">
            <div className="h-0.5 bg-gradient-to-r from-kserc-gold-dark via-kserc-gold to-kserc-gold-dark" />
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <p className="text-white/80 font-semibold text-sm">Kerala State Electricity Regulatory Commission</p>
                        <p className="text-xs mt-0.5">KPFC Bhavanam, C.V. Raman Pillai Road, Vellayambalam, Thiruvananthapuram - 695010</p>
                    </div>
                    <div className="text-right text-xs">
                        <p>Developed under the directives of KSERC</p>
                        <p className="text-white/40 mt-0.5">This is an automated analysis tool. Final orders are subject to Commission's approval.</p>
                    </div>
                </div>
            </div>
        </footer>
    )
}
