export default function Benchmarks() {
  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          <h2 className="font-serif text-[21px] font-bold text-navy">Regulatory Benchmarks & Rules</h2>
          <p className="text-[13px] text-[#445566] mt-1">Hardcoded KSERC regulatory logic active in the AI engine</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Benchmarks
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border">
            <h3 className="text-[13.5px] font-bold text-navy uppercase tracking-wider">Perennial Rejections (Always ₹0)</h3>
          </div>
          <div className="p-6 space-y-4">
            <div className="bg-gap/10 border-l-4 border-gap p-4 text-[13.5px] text-gap rounded-r">
              These items are <strong>rejected in every KSERC truing-up order</strong> without exception.
            </div>
            <table className="w-full text-[13.5px]">
              <thead className="bg-navy text-white text-[11.5px] font-bold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-2.5 text-left">Item</th>
                  <th className="px-4 py-2.5 text-left">Approved</th>
                  <th className="px-4 py-2.5 text-left">Basis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                <tr>
                  <td className="px-4 py-3 font-bold">Section 3(1) Electricity Duty</td>
                  <td className="px-4 py-3"><span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold">₹ 0</span></td>
                  <td className="px-4 py-3 text-[12px]">Cannot be passed to consumers</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 font-bold">CSR Expenses</td>
                  <td className="px-4 py-3"><span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold">₹ 0</span></td>
                  <td className="px-4 py-3 text-[12px]">Appropriation of profit, not distribution cost</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 font-bold">RPO Liability Provisions</td>
                  <td className="px-4 py-3"><span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold">₹ 0</span></td>
                  <td className="px-4 py-3 text-[12px]">Only actual REC payments allowed</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-border">
            <h3 className="text-[13.5px] font-bold text-navy uppercase tracking-wider">O&M Normative Cap Formula</h3>
          </div>
          <div className="p-6 space-y-4">
            <div className="bg-gold-kserc/10 border-l-4 border-gold-kserc p-4 text-[13.5px] text-gold-kserc rounded-r">
              Ref: KSERC Tariff Regulations 2021, Regulation 12(3)
            </div>
            <div className="text-[14px] leading-relaxed text-[#445566] space-y-4">
              <p>
                <strong>Formula:</strong><br />
                <code className="block bg-[#F0F2F5] p-3 rounded font-mono text-[13px] mt-2 border border-border">
                  Normative Cap = Prev. Approved × (1 + AICPI Rate)
                </code>
              </p>
              <p>
                If <strong>Actual &gt; Normative Cap</strong> → excess is disallowed.
              </p>
              <p>
                <strong>Exception:</strong> One-time documented expenditures (e.g., terminal benefit arrears, emergency repairs) may be approved over and above the cap if verified.
              </p>
              <p>
                <strong>Capital misclassification:</strong> Items &gt;₹5L claimed as R&amp;M but qualifying as capital are reclassified — only depreciation at approved rate is allowed.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-border">
          <h3 className="text-[13.5px] font-bold text-navy uppercase tracking-wider">Distribution Loss Efficiency Sharing</h3>
        </div>
        <div className="p-6">
          <div className="text-[14px] leading-relaxed text-[#445566] space-y-4">
            <p>
              When <strong>Actual Distribution Loss &lt; KSERC Target</strong>:
            </p>
            <div className="bg-[#F0F2F5] p-4 rounded border border-border space-y-2">
              <p className="font-mono text-[13px]">Efficiency Gain = (Target% − Actual%) × Energy Input (MU) ÷ 100</p>
              <p className="font-mono text-[13px]">Savings = Efficiency Gain × Power Purchase Cost per Unit</p>
            </div>
            <p>
              Licensee retains <strong>2/3</strong> of the resultant savings in power purchase cost.
            </p>
            <p className="italic text-[13px] bg-blue-kserc/5 p-3 rounded border border-blue-kserc/10">
              Example — Infopark FY2024-25: Target 4.23%, Actual 2.86% → Efficiency gain achieved → 2/3 of savings retained by licensee.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
