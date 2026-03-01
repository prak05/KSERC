import { useState, useEffect } from 'react';
import { HistoricalOrder } from '../types';

export default function HistoricalOrders() {
  const [history, setHistory] = useState<HistoricalOrder[]>([]);

  useEffect(() => {
    fetch('/api/history')
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(err => console.error('Error fetching history:', err));
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          <h2 className="font-serif text-[21px] font-bold text-navy">Historical Truing-Up Orders</h2>
          <p className="text-[13px] text-[#445566] mt-1">Past KSERC decisions — used as benchmarks for AI validation</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Historical Orders
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-border rounded-lg p-5 shadow-sm border-t-4 border-t-surplus">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#7A8A99] mb-2">All-Time Max Surplus</div>
          <div className="font-mono text-[22px] font-bold text-surplus leading-tight">₹ 280.42 L</div>
          <div className="text-[11px] text-[#7A8A99] mt-1.5">Technopark &nbsp;·&nbsp; FY 2020-21</div>
        </div>
        <div className="bg-white border border-border rounded-lg p-5 shadow-sm border-t-4 border-t-gap">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#7A8A99] mb-2">Max Approved Gap</div>
          <div className="font-mono text-[22px] font-bold text-gap leading-tight">₹ 64.72 L</div>
          <div className="text-[11px] text-[#7A8A99] mt-1.5">Infopark &nbsp;·&nbsp; FY 2024-25</div>
        </div>
        <div className="bg-white border border-border rounded-lg p-5 shadow-sm border-t-4 border-t-gold-kserc">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#7A8A99] mb-2">Notable Reversal</div>
          <div className="font-mono text-[22px] font-bold text-gold-kserc leading-tight">₹ 87.85 L</div>
          <div className="text-[11px] text-[#7A8A99] mt-1.5">CSEZA 2023-24 · Claimed deficit, got surplus</div>
        </div>
      </div>

      <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border">
          <h3 className="text-[13.5px] font-bold text-navy uppercase tracking-wider">All Historical Orders (Seeded from KSERC Research)</h3>
        </div>
        <table className="w-full text-[13.5px]">
          <thead className="bg-navy text-white text-[11.5px] font-bold uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">#</th>
              <th className="px-4 py-3 text-left">Licensee</th>
              <th className="px-4 py-3 text-left">Financial Year</th>
              <th className="px-4 py-3 text-right">Claimed (₹ L)</th>
              <th className="px-4 py-3 text-right">KSERC Approved (₹ L)</th>
              <th className="px-4 py-3 text-left">Outcome</th>
              <th className="px-4 py-3 text-left">Note</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {history.map((order, idx) => (
              <tr key={order.id} className="hover:bg-blue-kserc/5 transition-colors">
                <td className="px-4 py-3">{idx + 1}</td>
                <td className="px-4 py-3 font-medium">{order.licensee_code}</td>
                <td className="px-4 py-3">{order.financial_year}</td>
                <td className="px-4 py-3 text-right font-mono">
                  {order.claimed_lakhs !== null ? (order.claimed_lakhs > 0 ? `+${order.claimed_lakhs.toFixed(2)}` : order.claimed_lakhs.toFixed(2)) : '—'}
                </td>
                <td className={`px-4 py-3 text-right font-mono font-bold ${
                  order.approved_lakhs > 0 ? 'text-surplus' : 'text-gap'
                }`}>
                  {order.approved_lakhs > 0 ? `+${order.approved_lakhs.toFixed(2)}` : order.approved_lakhs.toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${
                    order.outcome_type === 'SURPLUS' ? 'bg-surplus/10 text-surplus' :
                    order.outcome_type === 'GAP' ? 'bg-gap/10 text-gap' :
                    'bg-gold-kserc/10 text-gold-kserc'
                  }`}>
                    ● {order.outcome_type}
                  </span>
                </td>
                <td className="px-4 py-3 text-[12px] text-[#7A8A99]">{order.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
