export default function Footer() {
    return (
        <footer className="bg-kserc-navy text-white/60 py-12">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-12 border-b border-white/10 pb-12 mb-8">
                    <div>
                        <div className="flex items-center gap-3 mb-6">
                            <div className="h-8 w-8 rounded-lg bg-white/10 flex items-center justify-center text-white font-serif text-lg font-bold border border-white/20">
                                K
                            </div>
                            <span className="text-lg font-bold text-white tracking-tight">KSERC</span>
                        </div>
                        <p className="text-sm leading-relaxed max-w-sm">
                            The Kerala State Electricity Regulatory Commission (KSERC) provides professional and transparent regulatory framework for the electricity sector in Kerala.
                        </p>
                    </div>

                    <div>
                        <h4 className="text-sm font-bold text-white uppercase tracking-widest mb-6">Quick Links</h4>
                        <ul className="space-y-4 text-sm">
                            <li><a href="#" className="hover:text-white transition-colors">Draft Regulations</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Commission Orders</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Consumer Grievance</a></li>
                            <li><a href="#" className="hover:text-white transition-colors">Tariff Schedule</a></li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="text-sm font-bold text-white uppercase tracking-widest mb-6">Internal Support</h4>
                        <p className="text-sm mb-4">Internal assistance for truing-up tools and AI-assisted auditing.</p>
                        <div className="p-4 bg-white/5 rounded-lg border border-white/10">
                            <p className="text-xs text-kserc-gold font-bold mb-1">AUDIT ASSISTANT HOTLINE</p>
                            <p className="text-sm text-white">0471-2735544</p>
                        </div>
                    </div>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-medium">
                    <p>© {new Date().getFullYear()} Kerala State Electricity Regulatory Commission. All Rights Reserved.</p>
                    <div className="flex items-center gap-6">
                        <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
                        <a href="#" className="hover:text-white transition-colors">Terms of Use</a>
                        <a href="#" className="hover:text-white transition-colors tracking-tight">Built for KSERC IT Cell</a>
                    </div>
                </div>
            </div>
        </footer>
    );
}
