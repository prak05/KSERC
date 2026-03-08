export default function GovBar() {
    return (
        <div className="bg-kserc-navy-dark text-white/70 text-[10px] py-1 font-medium tracking-widest uppercase">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <span>Government of Kerala | കേരള സർക്കാർ</span>
                    <span className="hidden sm:inline border-l border-white/20 pl-4">Department of Power</span>
                </div>
                <div className="hidden md:flex items-center gap-6">
                    <a href="#" className="hover:text-white transition-colors">English</a>
                    <a href="#" className="hover:text-white transition-colors font-malayalam">മലയാളം</a>
                </div>
            </div>
        </div>
    );
}
