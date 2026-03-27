import { Plus, CheckCircle, Clock, ArrowRight, X } from 'lucide-react';

interface DashboardProps {
  onStartAnalysis: () => void;
  completedReports: Record<string, { gap: number, type: 'gap' | 'surplus' }>;
  onClearReport: (licensee: string) => void;
}

export default function Dashboard({ onStartAnalysis, completedReports, onClearReport }: DashboardProps) {
  const baseKpis = [
    { licensee: 'Infoparks Kerala', status: 'GAP', value: 'Pending', year: 'FY 2024-25', type: 'pending' },
    { licensee: 'Technopark', status: 'SURPLUS', value: 'Pending', year: 'FY 2024-25', type: 'pending' },
    { licensee: 'KDHPCL', status: 'SURPLUS', value: 'Pending', year: 'FY 2024-25', type: 'pending' },
    { licensee: 'CSEZA', status: 'GAP', value: 'Pending', year: 'FY 2024-25', type: 'pending' },
  ];

  const kpis = baseKpis.map(kpi => {
    const completed = completedReports[kpi.licensee];
    if (completed) {
      return {
        ...kpi,
        status: completed.type.toUpperCase(),
        value: `₹ ${completed.gap.toFixed(2)} L`,
        type: completed.type
      };
    }
    return kpi;
  });

  const recentActivity = [
    { text: 'Infopark FY2024-25 — Analysis Complete', date: 'Today' },
    { text: 'CSEZA FY2023-24 — Pending Review', date: 'Yesterday' },
    { text: 'KDHPCL FY2022-23 — Report Generated', date: '2 days ago' },
  ];

  return (
    <div className="space-y-10">
      <div className="flex items-start justify-between border-b border-border pb-6">
        <div>
          <h2 className="font-serif text-2xl font-bold text-navy">Dashboard</h2>
          <p className="text-sm text-[#5A6A7A] mt-1.5">FY 2024-25 Summary & Recent Regulatory Activity</p>
        </div>
        <div className="text-[12px] text-[#7A8A99] font-medium">
          <span className="text-blue-kserc">Home</span> › Dashboard
        </div>
      </div>

      <div className="space-y-6">
        <h3 className="text-[11px] font-bold text-navy uppercase tracking-widest">FY 2024-25 Summary</h3>
        <div className="grid grid-cols-4 gap-6">
          {kpis.map((kpi, idx) => (
            <div
              key={idx}
              className="bg-white border border-border rounded-lg p-6 shadow-sm hover:shadow-md transition-all border-t-4 border-t-navy relative group"
            >
              {completedReports[kpi.licensee] && (
                <button 
                  onClick={() => onClearReport(kpi.licensee)}
                  className="absolute top-2 right-2 p-1 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Clear Analysis"
                >
                  <X size={14} />
                </button>
              )}
              <div className="text-[10px] font-bold uppercase tracking-widest text-[#7A8A99] mb-3">
                {kpi.licensee}
              </div>
              <div className={`text-[11px] font-bold mb-1 ${
                kpi.type === 'gap' ? 'text-gap' : kpi.type === 'surplus' ? 'text-surplus' : 'text-gold-kserc'
              }`}>
                {kpi.status}
              </div>
              <div className={`font-mono text-2xl font-bold leading-tight ${
                kpi.type === 'gap' ? 'text-gap' : kpi.type === 'surplus' ? 'text-surplus' : 'text-slate-300'
              }`}>
                {kpi.value}
              </div>
              <div className="text-[10px] text-[#7A8A99] mt-4 font-medium uppercase tracking-tighter">
                {kpi.year}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2 bg-white border border-border rounded-lg shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-border bg-slate-50 flex items-center justify-between">
            <h3 className="text-[11px] font-bold text-navy uppercase tracking-widest">Recent Activity</h3>
          </div>
          <div className="p-6 space-y-4">
            {recentActivity.map((activity, idx) => (
              <div key={idx} className="flex items-center justify-between py-3 border-b border-border last:border-0 group cursor-pointer">
                <div className="flex items-center gap-4">
                  <div className="w-2 h-2 rounded-full bg-blue-kserc group-hover:scale-125 transition-transform" />
                  <span className="text-sm font-medium text-navy group-hover:text-blue-kserc transition-colors">{activity.text}</span>
                </div>
                <span className="text-[11px] text-[#7A8A99] font-bold uppercase">{activity.date}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-navy rounded-lg p-8 flex flex-col justify-center items-center text-center space-y-6 shadow-xl border-b-4 border-gold-kserc">
          <div className="h-16 w-16 bg-white/10 rounded-full flex items-center justify-center border border-white/20">
            <Plus size={32} className="text-gold-kserc" />
          </div>
          <div className="space-y-2">
            <h3 className="text-white font-bold text-lg">New Analysis</h3>
            <p className="text-[#A8C0D8] text-xs leading-relaxed">
              Start a new truing-up analysis by uploading licensee documents.
            </p>
          </div>
          <button
            onClick={onStartAnalysis}
            className="w-full bg-blue-kserc text-white font-bold py-3 rounded-md hover:bg-[#174E8C] transition-all flex items-center justify-center gap-2 shadow-lg uppercase tracking-widest text-xs"
          >
            Start New Analysis <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
