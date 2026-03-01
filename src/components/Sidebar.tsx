import { Page } from '../types';
import { LayoutDashboard, Upload, Calculator, History, Info, FileText } from 'lucide-react';

interface SidebarProps {
  activePage: Page;
  onPageChange: (page: Page) => void;
}

export default function Sidebar({ activePage, onPageChange }: SidebarProps) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'upload', label: 'Upload & Analyse', icon: Upload },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'history', label: 'Historical Orders', icon: History },
    { id: 'benchmarks', label: 'Benchmarks', icon: Info },
  ] as const;

  return (
    <nav className="w-64 bg-navy-mid flex-shrink-0 flex flex-col border-r border-white/10">
      <div className="text-[10px] font-bold text-white/35 tracking-[1.2px] uppercase px-5 pt-6 pb-2">
        Navigation
      </div>
      <div className="flex-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onPageChange(item.id as Page)}
              className={`w-full flex items-center gap-3 px-5 py-3 text-[13.5px] font-medium transition-all border-l-4 ${
                isActive
                  ? 'bg-blue-kserc/35 text-white border-gold-kserc'
                  : 'text-white/70 border-transparent hover:bg-white/10 hover:text-white hover:border-gold-kserc/50'
              }`}
            >
              <Icon size={16} className="opacity-85" />
              {item.label}
            </button>
          );
        })}
      </div>
      <div className="mt-auto p-5 border-t border-white/10 text-[11px] text-white/30 leading-relaxed">
        <div>Developed by RIET, Thiruvananthapuram</div>
        <div className="mt-1">Under KSERC Work Order KSERC/CSO/03-05</div>
        <div className="mt-2 text-white/50">Confidential — Authorised Use Only</div>
      </div>
    </nav>
  );
}
