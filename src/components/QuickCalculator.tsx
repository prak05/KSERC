import { useState } from 'react';
import { CalculationResult } from '../types';

export default function QuickCalculator() {
  const [arr, setArr] = useState('');
  const [rev, setRev] = useState('');
  const [result, setResult] = useState<CalculationResult | null>(null);

  const [atcInput, setAtcInput] = useState('');
  const [atcSold, setAtcSold] = useState('');
  const [atcTarget, setAtcTarget] = useState('');
  const [atcResult, setAtcResult] = useState<{ loss: number; note: string; type: 'surplus' | 'gap' } | null>(null);

  const runCalc = async () => {
    if (!arr || !rev) return;
    const response = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved_arr: parseFloat(arr), actual_revenue: parseFloat(rev) }),
    });
    const data = await response.json();
    setResult(data);
  };

  const runAtcCalc = () => {
    const input = parseFloat(atcInput);
    const sold = parseFloat(atcSold);
    const target = parseFloat(atcTarget);

    if (isNaN(input) || isNaN(sold)) return;

    const loss = ((input - sold) / input) * 100;
    let note = '';
    let type: 'surplus' | 'gap' = 'gap';

    if (!isNaN(target)) {
      const effGain = loss < target;
      type = effGain ? 'surplus' : 'gap';
      const gainPct = target - loss;
      note = effGain
        ? `Efficiency gain: ${gainPct.toFixed(2)}%. Licensee retains 2/3 of power purchase savings.`
        : `Loss exceeds target by ${(loss - target).toFixed(2)}%.`;
    } else {
      note = `Formula: (${input} − ${sold}) ÷ ${input} × 100`;
    }

    setAtcResult({ loss, note, type });
  };

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          <h2 className="font-serif text-[21px] font-bold text-navy">Quick Revenue Gap Calculator</h2>
          <p className="text-[13px] text-[#445566] mt-1">Manually enter figures to compute Revenue Gap or Surplus instantly</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Quick Calculator
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border">
            <h3 className="text-[13.5px] font-bold text-navy uppercase tracking-wider">Revenue Gap Calculator</h3>
          </div>
          <div className="p-6 space-y-5">
            <div className="bg-[#EBF4FD] border-l-4 border-blue-kserc p-4 text-[13.5px] text-[#0C4A7A] rounded-r">
              <strong>Formula:</strong> Revenue Gap = Approved ARR − Actual Revenue
              &nbsp;|&nbsp; Positive = Gap &nbsp;|&nbsp; Negative = Surplus
            </div>

            <div className="space-y-1.5">
              <label className="text-[13px] font-semibold text-[#1C2B3A]">Approved ARR (₹ Lakh) <span className="text-gap">*</span></label>
              <input
                type="number"
                value={arr}
                onChange={(e) => setArr(e.target.value)}
                placeholder="e.g. 315.80"
                className="w-full p-2.5 border-1.5 border-border rounded-md text-[14px] font-mono focus:outline-none focus:border-blue-kserc focus:ring-3 focus:ring-blue-kserc/15"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[13px] font-semibold text-[#1C2B3A]">Actual Revenue Collected (₹ Lakh) <span className="text-gap">*</span></label>
              <input
                type="number"
                value={rev}
                onChange={(e) => setRev(e.target.value)}
                placeholder="e.g. 251.08"
                className="w-full p-2.5 border-1.5 border-border rounded-md text-[14px] font-mono focus:outline-none focus:border-blue-kserc focus:ring-3 focus:ring-blue-kserc/15"
              />
            </div>

            <button
              onClick={runCalc}
              className="w-full bg-blue-kserc text-white font-bold py-3 rounded-md shadow-md hover:bg-[#174E8C] transition-all uppercase tracking-wider text-[13.5px]"
            >
              ≡ Calculate Revenue Gap / Surplus
            </button>

            {result && (
              <div
                className={`text-center p-6 rounded-lg border-1.5 transition-all ${
                  result.outcome === 'GAP' ? 'bg-gap/10 border-gap' : 'bg-surplus/10 border-surplus'
                }`}
              >
                <div className="text-[12px] font-bold uppercase tracking-wider text-[#7A8A99]">
                  {result.outcome === 'GAP' ? 'Revenue Gap (Licensee is owed)' : 'Revenue Surplus (Licensee collected excess)'}
                </div>
                <div className={`font-mono text-[32px] font-bold mt-1.5 ${
                  result.outcome === 'GAP' ? 'text-gap' : 'text-surplus'
                }`}>
                  ₹ {Math.abs(result.gap_amount).toFixed(2)} Lakh
                </div>
                <div className="text-[12px] text-[#7A8A99] mt-1 font-medium">
                  {result.is_anomaly
                    ? '⚠ ANOMALY: Result outside historical range (₹-280.42L to ₹+64.72L).'
                    : `Within historical bounds · Formula: ${arr} − ${rev} = ${result.gap_amount}`}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border">
            <h3 className="text-[13.5px] font-bold text-navy uppercase tracking-wider">AT&amp;C Loss Calculator</h3>
          </div>
          <div className="p-6 space-y-5">
            <div className="bg-[#EBF4FD] border-l-4 border-blue-kserc p-4 text-[13.5px] text-[#0C4A7A] rounded-r">
              <strong>Formula:</strong> AT&amp;C Loss (%) = (Energy Input − Energy Realized) ÷ Energy Input × 100
            </div>

            <div className="space-y-1.5">
              <label className="text-[13px] font-semibold text-[#1C2B3A]">Energy Input (Million Units)</label>
              <input
                type="number"
                value={atcInput}
                onChange={(e) => setAtcInput(e.target.value)}
                placeholder="e.g. 1000.00"
                className="w-full p-2.5 border-1.5 border-border rounded-md text-[14px] font-mono focus:outline-none focus:border-blue-kserc focus:ring-3 focus:ring-blue-kserc/15"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[13px] font-semibold text-[#1C2B3A]">Energy Sold to Consumers (Million Units)</label>
              <input
                type="number"
                value={atcSold}
                onChange={(e) => setAtcSold(e.target.value)}
                placeholder="e.g. 971.40"
                className="w-full p-2.5 border-1.5 border-border rounded-md text-[14px] font-mono focus:outline-none focus:border-blue-kserc focus:ring-3 focus:ring-blue-kserc/15"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[13px] font-semibold text-[#1C2B3A]">KSERC Approved Target Loss (%)</label>
              <input
                type="number"
                value={atcTarget}
                onChange={(e) => setAtcTarget(e.target.value)}
                placeholder="e.g. 4.23"
                className="w-full p-2.5 border-1.5 border-border rounded-md text-[14px] font-mono focus:outline-none focus:border-blue-kserc focus:ring-3 focus:ring-blue-kserc/15"
              />
            </div>

            <button
              onClick={runAtcCalc}
              className="w-full bg-white text-blue-kserc font-bold py-3 rounded-md border-1.5 border-blue-kserc hover:bg-blue-kserc/5 transition-all uppercase tracking-wider text-[13.5px]"
            >
              Calculate AT&amp;C Loss
            </button>

            {atcResult && (
              <div
                className={`text-center p-6 rounded-lg border-1.5 transition-all ${
                  atcResult.type === 'gap' ? 'bg-gap/10 border-gap' : 'bg-surplus/10 border-surplus'
                }`}
              >
                <div className="text-[12px] font-bold uppercase tracking-wider text-[#7A8A99]">AT&amp;C Loss</div>
                <div className={`font-mono text-[32px] font-bold mt-1.5 ${
                  atcResult.type === 'gap' ? 'text-gap' : 'text-surplus'
                }`}>
                  {atcResult.loss.toFixed(2)} %
                </div>
                <div className="text-[12px] text-[#7A8A99] mt-1 font-medium">
                  {atcResult.note}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
