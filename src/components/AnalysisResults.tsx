import { CheckCircle, AlertTriangle, XCircle, Eye, FileText } from 'lucide-react';
import { LineItem } from '../types';

interface AnalysisResultsProps {
  licensee: string;
  year: string;
  lineItems: LineItem[];
  onViewReasoning: (item: string) => void;
  onGenerateReport: () => void;
}

export default function AnalysisResults({ licensee, year, lineItems, onViewReasoning, onGenerateReport }: AnalysisResultsProps) {
  const totalClaimed = lineItems.reduce((acc, item) => acc + item.claimed, 0);
  const totalApproved = lineItems.reduce((acc, item) => acc + item.approved, 0);
  const disallowed = totalClaimed - totalApproved;

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          <h2 className="font-serif text-[21px] font-bold text-navy">Analysis Results: {licensee} — {year}</h2>
          <p className="text-[13px] text-[#445566] mt-1">Review AI recommendations and finalize line-item approvals</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Results
        </div>
      </div>

      <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
        <div className="p-8 bg-slate-50 border-b border-border">
          <h3 className="text-[11px] font-bold text-navy uppercase tracking-widest mb-4">Summary</h3>
          <div className="grid grid-cols-3 gap-8">
            <div className="space-y-1">
              <div className="text-[12px] text-[#7A8A99] font-medium">Claimed Gap</div>
              <div className="font-mono text-2xl font-bold text-navy">₹ {totalClaimed.toFixed(2)} Lakh</div>
            </div>
            <div className="space-y-1">
              <div className="text-[12px] text-[#7A8A99] font-medium">Recommended Gap</div>
              <div className="font-mono text-2xl font-bold text-gap">₹ {totalApproved.toFixed(2)} Lakh</div>
            </div>
            <div className="space-y-1">
              <div className="text-[12px] text-[#7A8A99] font-medium">Disallowed Amount</div>
              <div className="font-mono text-2xl font-bold text-slate-500">₹ {disallowed.toFixed(2)} Lakh</div>
            </div>
          </div>
        </div>

        <div className="p-0">
          <div className="px-8 py-4 border-b border-border bg-white">
            <h3 className="text-[11px] font-bold text-navy uppercase tracking-widest">Line-Item Validation</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-navy text-white text-[11px] font-bold uppercase tracking-widest">
              <tr>
                <th className="px-8 py-3 text-left">Item</th>
                <th className="px-8 py-3 text-right">Claimed (₹L)</th>
                <th className="px-8 py-3 text-right">Approved (₹L)</th>
                <th className="px-8 py-3 text-center">Status</th>
                <th className="px-8 py-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {lineItems.map((item) => (
                <tr key={item.name} className="hover:bg-blue-kserc/5 transition-colors group">
                  <td className="px-8 py-4 font-semibold text-navy">{item.name}</td>
                  <td className="px-8 py-4 text-right font-mono text-[#5A6A7A]">₹ {item.claimed.toFixed(2)}</td>
                  <td className={`px-8 py-4 text-right font-mono font-bold ${item.approved === 0 ? 'text-slate-400' : 'text-navy'}`}>
                    ₹ {item.approved.toFixed(2)}
                  </td>
                  <td className="px-8 py-4 text-center">
                    <div className="flex justify-center">
                      {item.status === 'pass' && (
                        <span className="bg-surplus/10 text-surplus px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5">
                          <CheckCircle size={12} /> Pass
                        </span>
                      )}
                      {item.status === 'flagged' && (
                        <span className="bg-flag/10 text-flag px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5">
                          <AlertTriangle size={12} /> Flagged
                        </span>
                      )}
                      {item.status === 'rejected' && (
                        <span className="bg-gap/10 text-gap px-2.5 py-1 rounded text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5">
                          <XCircle size={12} /> Rejected
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-8 py-4 text-center">
                    <div className="flex justify-center gap-2">
                      <button 
                        onClick={() => onViewReasoning(item.name)}
                        className="p-2 text-blue-kserc hover:bg-blue-kserc/10 rounded-md transition-all flex items-center gap-1.5 text-[11px] font-bold uppercase"
                      >
                        <Eye size={14} /> {item.status === 'flagged' ? 'Review' : 'View'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-8 bg-slate-50 border-t border-border flex justify-between items-center">
          <button className="text-blue-kserc font-bold text-sm uppercase tracking-widest hover:underline">
            View Full AI Reasoning Report
          </button>
          <div className="flex gap-4">
            <button className="px-8 py-3 bg-white border border-border text-[#445566] font-bold rounded-md hover:bg-slate-100 transition-all text-sm uppercase tracking-widest">
              Modify All
            </button>
            <button 
              onClick={onGenerateReport}
              className="px-8 py-3 bg-blue-kserc text-white font-bold rounded-md shadow-lg hover:bg-[#174E8C] transition-all uppercase tracking-widest text-sm flex items-center gap-2"
            >
              Generate Report <FileText size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
