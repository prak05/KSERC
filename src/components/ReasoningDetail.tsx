import { useState } from 'react';
import { ArrowLeft, CheckCircle, Info, Save } from 'lucide-react';
import { LineItem } from '../types';
import { motion } from 'motion/react';

interface ReasoningDetailProps {
  item: LineItem;
  onUpdate: (updates: Partial<LineItem>) => void;
  onBack: () => void;
}

export default function ReasoningDetail({ item, onUpdate, onBack }: ReasoningDetailProps) {
  const [decision, setDecision] = useState<'recommendation' | 'override' | 'flag'>('recommendation');
  const [overrideAmount, setOverrideAmount] = useState<string>(item.approved.toString());
  const [isSaving, setIsSaving] = useState(false);
  const [showSaved, setShowSaved] = useState(false);

  const handleSave = () => {
    setIsSaving(true);
    setTimeout(() => {
      let finalApproved = item.approved;
      let finalStatus = item.status;

      if (decision === 'recommendation') {
        // Keep as is or reset to original recommendation if it was changed
        // For simplicity, let's assume item.approved is the recommendation
      } else if (decision === 'override') {
        finalApproved = parseFloat(overrideAmount) || 0;
        finalStatus = finalApproved === item.claimed ? 'pass' : 'flagged';
      } else if (decision === 'flag') {
        finalStatus = 'flagged';
      }

      onUpdate({ approved: finalApproved, status: finalStatus });
      setIsSaving(false);
      setShowSaved(true);
      setTimeout(() => setShowSaved(false), 2000);
    }, 800);
  };

  const disallowed = item.claimed - item.approved;

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          <button 
            onClick={onBack}
            className="flex items-center gap-2 text-blue-kserc font-bold text-[11px] uppercase tracking-widest mb-4 hover:underline"
          >
            <ArrowLeft size={14} /> Back to Results
          </button>
          <h2 className="font-serif text-[21px] font-bold text-navy">AI Reasoning: {item.name}</h2>
          <p className="text-[13px] text-[#445566] mt-1">Detailed regulatory basis for the recommended approval amount</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Reasoning
        </div>
      </div>

      {showSaved && (
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-surplus/10 border border-surplus/20 text-surplus p-4 rounded-lg flex items-center gap-3"
        >
          <CheckCircle size={20} />
          <span className="text-sm font-bold">Decision saved successfully!</span>
        </motion.div>
      )}

      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2 space-y-6">
          <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-border bg-slate-50 flex items-center justify-between">
              <h3 className="text-[11px] font-bold text-navy uppercase tracking-widest">Analysis Breakdown</h3>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                item.status === 'pass' ? 'bg-surplus/10 text-surplus' : 
                item.status === 'flagged' ? 'bg-flag/10 text-flag' : 'bg-gap/10 text-gap'
              }`}>
                {item.status === 'pass' ? 'Validated' : item.status === 'flagged' ? 'Review Required' : 'Rejected'}
              </span>
            </div>
            <div className="p-8 space-y-8">
              <div className="grid grid-cols-3 gap-6">
                <div className="space-y-1">
                  <div className="text-[11px] text-[#7A8A99] font-bold uppercase tracking-tighter">Claimed by Licensee</div>
                  <div className="font-mono text-xl font-bold text-navy">₹ {item.claimed.toFixed(2)} Lakh</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[11px] text-[#7A8A99] font-bold uppercase tracking-tighter">Current Approved</div>
                  <div className="font-mono text-xl font-bold text-surplus">₹ {item.approved.toFixed(2)} Lakh</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[11px] text-[#7A8A99] font-bold uppercase tracking-tighter">Disallowed Amount</div>
                  <div className="font-mono text-xl font-bold text-gap">₹ {disallowed.toFixed(2)} Lakh</div>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-[11px] font-bold text-navy uppercase tracking-widest flex items-center gap-2">
                  <Info size={14} className="text-blue-kserc" /> AI Reasoning
                </h4>
                <div className="bg-blue-kserc/5 border border-blue-kserc/10 rounded-lg p-6 text-sm leading-relaxed text-[#1C2B3A] space-y-4">
                  <p>
                    Based on <strong>KSERC Tariff Regulations 2021, Regulation 12(3)</strong>: {item.name} costs are capped at the normative level escalated by the AICPI index (4.2% for FY25).
                  </p>
                  <div className="bg-white border border-border rounded p-4 font-mono text-[12px] space-y-1 shadow-sm">
                    <div className="flex justify-between"><span>Approved (FY24)</span> <span>₹ {(item.approved / 1.042).toFixed(2)} Lakh</span></div>
                    <div className="flex justify-between text-blue-kserc"><span>Normative (FY25) = ₹{(item.approved / 1.042).toFixed(2)} × 1.042</span> <span>₹ {item.approved.toFixed(2)} Lakh</span></div>
                    <div className="flex justify-between border-t border-border mt-2 pt-2"><span>Claimed (FY25)</span> <span>₹ {item.claimed.toFixed(2)} Lakh</span></div>
                    <div className="flex justify-between text-gap font-bold"><span>Excess Disallowed</span> <span>₹ {disallowed.toFixed(2)} Lakh</span></div>
                  </div>
                  <p className="text-[#5A6A7A] italic text-[12px]">
                    Reference: Past Order — Infopark FY2020-21 (same logic applied; excess of ₹2.1L was disallowed).
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-border bg-navy">
              <h3 className="text-[11px] font-bold text-white uppercase tracking-widest">Staff Decision</h3>
            </div>
            <div className="p-6 space-y-6">
              <div className="space-y-4">
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input 
                    type="radio" 
                    name="decision" 
                    className="mt-1 accent-blue-kserc" 
                    checked={decision === 'recommendation'}
                    onChange={() => setDecision('recommendation')}
                  />
                  <div className="text-sm">
                    <div className="font-bold text-navy group-hover:text-blue-kserc transition-colors">Accept AI Recommendation</div>
                    <div className="text-[11px] text-[#7A8A99] mt-0.5">Approve ₹ {item.approved.toFixed(2)} Lakh as per normative cap</div>
                  </div>
                </label>
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input 
                    type="radio" 
                    name="decision" 
                    className="mt-1 accent-blue-kserc" 
                    checked={decision === 'override'}
                    onChange={() => setDecision('override')}
                  />
                  <div className="text-sm">
                    <div className="font-bold text-navy group-hover:text-blue-kserc transition-colors">Override Recommendation</div>
                    <div className="text-[11px] text-[#7A8A99] mt-0.5">Enter a custom approval amount</div>
                  </div>
                </label>
                <label className="flex items-start gap-3 cursor-pointer group">
                  <input 
                    type="radio" 
                    name="decision" 
                    className="mt-1 accent-blue-kserc" 
                    checked={decision === 'flag'}
                    onChange={() => setDecision('flag')}
                  />
                  <div className="text-sm">
                    <div className="font-bold text-navy group-hover:text-blue-kserc transition-colors">Flag for Senior Review</div>
                    <div className="text-[11px] text-[#7A8A99] mt-0.5">Escalate to Commissioner for final decision</div>
                  </div>
                </label>
              </div>

              {decision === 'override' && (
                <div className="space-y-2">
                  <label className="text-[11px] font-bold text-navy uppercase tracking-widest">Override Amount (₹L)</label>
                  <input 
                    type="number" 
                    className="w-full p-3 border border-border rounded-md font-mono text-sm focus:outline-none focus:border-blue-kserc" 
                    value={overrideAmount}
                    onChange={(e) => setOverrideAmount(e.target.value)}
                    placeholder="0.00"
                  />
                </div>
              )}

              <button 
                onClick={handleSave}
                disabled={isSaving}
                className="w-full bg-blue-kserc text-white font-bold py-3 rounded-md shadow-lg hover:bg-[#174E8C] disabled:bg-slate-400 transition-all uppercase tracking-widest text-[12px] flex items-center justify-center gap-2"
              >
                {isSaving ? 'Saving...' : <><Save size={16} /> Save Decision</>}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
