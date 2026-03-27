import { LogOut } from 'lucide-react';

interface HeaderProps {
  onLogout: () => void;
}

export default function Header({ onLogout }: HeaderProps) {
  return (
    <header className="bg-navy text-white sticky top-0 z-50 shadow-lg flex-shrink-0">
      <div className="h-1 bg-gradient-to-r from-gold-kserc via-[#D4A017] to-gold-kserc"></div>
      <div className="px-6 py-2.5 flex items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 bg-white/10 rounded-full flex items-center justify-center border border-white/20">
            <span className="text-[10px] font-bold text-gold-kserc text-center leading-tight">KERALA<br/>STATE</span>
          </div>
          <div className="w-[1px] h-11 bg-white/25"></div>
          <div className="h-11 w-11 bg-white/10 rounded-full flex items-center justify-center border border-white/20">
            <span className="text-[10px] font-bold text-gold-kserc text-center leading-tight">KSERC<br/>LOGO</span>
          </div>
        </div>
        <div className="flex-1">
          <h1 className="font-serif text-base font-bold tracking-wide leading-tight">
            Kerala State Electricity Regulatory Commission
          </h1>
          <p className="text-[11px] text-[#A8C0D8] mt-0.5">
            AI-Based Truing-Up Analytical Tool &nbsp;|&nbsp; Work Order No. KSERC/CSO/03-05
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-[11px] font-bold text-white uppercase tracking-wider">User: Staff</div>
            <button 
              onClick={onLogout}
              className="text-[10px] text-[#F5D87A] hover:underline flex items-center gap-1 ml-auto"
            >
              <LogOut size={10} /> Logout
            </button>
          </div>
          <div className="bg-gold-kserc/25 border border-gold-kserc/50 text-[#F5D87A] text-[10px] font-bold px-2.5 py-0.5 rounded uppercase tracking-wider">
            Prototype v1.0
          </div>
        </div>
      </div>
    </header>
  );
}
