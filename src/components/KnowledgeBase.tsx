import { useState, useEffect } from 'react';
import { Book, Search, History, Shield, TrendingUp, AlertTriangle } from 'lucide-react';

interface KnowledgeSection {
  id: number;
  section_name: string;
  content: string;
  updated_at: string;
}

export default function KnowledgeBase() {
  const [sections, setSections] = useState<KnowledgeSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetch('/api/rules')
      .then(res => res.json())
      .then(data => {
        setSections(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching rules:', err);
        setLoading(false);
      });
  }, []);

  const filteredSections = sections.filter(s => 
    s.section_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.content.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          <h2 className="font-serif text-[21px] font-bold text-navy">Knowledge Base</h2>
          <p className="text-[13px] text-[#445566] mt-1">Legal framework, tariff norms and historical benchmarks for FY 2026</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Knowledge Base
        </div>
      </div>

      <div className="relative max-w-2xl">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
        <input
          type="text"
          placeholder="Search rules, regulations or benchmarks..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-3 border border-border rounded-lg bg-white shadow-sm focus:outline-none focus:border-blue-kserc focus:ring-2 focus:ring-blue-kserc/10"
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          {loading ? (
            <div className="animate-pulse space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-40 bg-slate-200 rounded-lg"></div>
              ))}
            </div>
          ) : filteredSections.length > 0 ? (
            filteredSections.map(section => (
              <div key={section.id} className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-border bg-slate-50 flex items-center gap-3">
                  <Book size={18} className="text-navy" />
                  <h3 className="font-bold text-navy">{section.section_name}</h3>
                </div>
                <div className="p-6">
                  <pre className="text-sm text-[#445566] whitespace-pre-wrap font-sans leading-relaxed">
                    {section.content}
                  </pre>
                  <div className="mt-6 text-[11px] text-[#7A8A99] uppercase font-bold tracking-tighter">
                    Last Updated: {new Date(section.updated_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-12 text-center bg-white border border-dashed border-border rounded-lg">
              <Book size={48} className="mx-auto text-slate-200 mb-4" />
              <p className="text-slate-400 font-medium">No matching rules found in the knowledge base.</p>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-navy rounded-lg p-6 text-white shadow-lg">
            <h4 className="font-bold text-sm mb-4 flex items-center gap-2">
              <Shield size={16} className="text-gold-kserc" />
              Quick Reference
            </h4>
            <div className="space-y-4">
              <div className="p-3 bg-white/10 rounded border border-white/10">
                <div className="text-[10px] text-white/50 uppercase font-bold mb-1">Max Approved Surplus</div>
                <div className="text-lg font-bold">₹ 280.42 L</div>
              </div>
              <div className="p-3 bg-white/10 rounded border border-white/10">
                <div className="text-[10px] text-white/50 uppercase font-bold mb-1">Max Approved Gap</div>
                <div className="text-lg font-bold">₹ 64.72 L</div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-border rounded-lg p-6 shadow-sm">
            <h4 className="font-bold text-navy text-sm mb-4 flex items-center gap-2">
              <TrendingUp size={16} className="text-blue-kserc" />
              Escalation Norms
            </h4>
            <ul className="text-xs space-y-3 text-[#445566]">
              <li className="flex justify-between border-b border-slate-50 pb-2">
                <span>Employee Exp.</span>
                <span className="font-bold text-navy">4.2% / yr</span>
              </li>
              <li className="flex justify-between border-b border-slate-50 pb-2">
                <span>R&M Cap</span>
                <span className="font-bold text-navy">6.0% / yr</span>
              </li>
              <li className="flex justify-between border-b border-slate-50 pb-2">
                <span>Working Cap Interest</span>
                <span className="font-bold text-navy">8.25%</span>
              </li>
            </ul>
          </div>

          <div className="bg-gap/5 border border-gap/20 rounded-lg p-6">
            <h4 className="font-bold text-gap text-sm mb-4 flex items-center gap-2">
              <AlertTriangle size={16} />
              Perennial Rejections
            </h4>
            <ul className="text-[11px] space-y-3 text-gap/80 leading-relaxed list-disc pl-4">
              <li>Section 3(1) Electricity Duty</li>
              <li>CSR Expenses (from profit only)</li>
              <li>Provisions for Doubtful Debts</li>
              <li>REC Provisioning (without REC buy)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
