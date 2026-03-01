import { useState, useRef, ChangeEvent } from 'react';
import { Licensee } from '../types';
import { Upload, FileText, X, ArrowRight } from 'lucide-react';

interface UploadAnalyseProps {
  licensees: Licensee[];
  onStartAnalysis: (licensee: string, year: string) => void;
}

interface DocumentUploadSlot {
  id: string;
  label: string;
  mandatory: boolean;
  file: File | null;
}

export default function UploadAnalyse({ licensees, onStartAnalysis }: UploadAnalyseProps) {
  const [selectedLicensee, setSelectedLicensee] = useState('');
  const [selectedYear, setSelectedYear] = useState('2024-25');

  const [uploadSlots, setUploadSlots] = useState<DocumentUploadSlot[]>([
    { id: 'annual_accounts', label: 'Audited Annual Accounts (PDF)', mandatory: true, file: null },
    { id: 'arr_order', label: 'ARR Order for FY 2024-25 (PDF)', mandatory: true, file: null },
    { id: 'prev_truing_up', label: 'Previous Year Truing-Up Order (PDF)', mandatory: true, file: null },
    { id: 'energy_audit', label: 'Energy Audit Statement (PDF/Excel)', mandatory: false, file: null },
    { id: 'tariff_schedule', label: 'Tariff Schedule (PDF)', mandatory: false, file: null },
  ]);

  const fileInputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({});

  const handleFileChange = (slotId: string, e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const newFile = e.target.files[0];
      setUploadSlots(prev => prev.map(slot => 
        slot.id === slotId ? { ...slot, file: newFile } : slot
      ));
    }
  };

  const removeFile = (slotId: string) => {
    setUploadSlots(prev => prev.map(slot => 
      slot.id === slotId ? { ...slot, file: null } : slot
    ));
    if (fileInputRefs.current[slotId]) {
      fileInputRefs.current[slotId]!.value = '';
    }
  };

  const isMandatoryUploaded = uploadSlots
    .filter(s => s.mandatory)
    .every(s => s.file !== null);

  const handleRunAnalysis = () => {
    if (isMandatoryUploaded && selectedLicensee) {
      onStartAnalysis(selectedLicensee, selectedYear);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          <h2 className="font-serif text-[21px] font-bold text-navy">Upload Documents</h2>
          <p className="text-[13px] text-[#445566] mt-1">Follow the 3-step process to begin truing-up analysis</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Upload
        </div>
      </div>

      <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
        {/* Step 1 */}
        <div className="p-8 border-b border-border">
          <div className="flex items-center gap-4 mb-6">
            <div className="h-8 w-8 bg-navy text-white rounded-full flex items-center justify-center font-bold text-sm">1</div>
            <h3 className="text-lg font-bold text-navy">Step 1 of 3: Select Licensee & Year</h3>
          </div>
          
          <div className="grid grid-cols-2 gap-8 max-w-3xl">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-navy">Distribution Licensee:</label>
              <select
                value={selectedLicensee}
                onChange={(e) => setSelectedLicensee(e.target.value)}
                className="w-full p-3 border border-border rounded-md text-sm focus:outline-none focus:border-blue-kserc focus:ring-2 focus:ring-blue-kserc/10 transition-all"
              >
                <option value="">— Select Licensee —</option>
                {licensees.map((l) => (
                  <option key={l.id} value={l.name}>{l.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-navy">Financial Year:</label>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                className="w-full p-3 border border-border rounded-md text-sm focus:outline-none focus:border-blue-kserc focus:ring-2 focus:ring-blue-kserc/10 transition-all"
              >
                {['2024-25', '2023-24', '2022-23', '2021-22', '2020-21'].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Step 2 */}
        <div className="p-8 border-b border-border bg-slate-50/50">
          <div className="flex items-center gap-4 mb-6">
            <div className="h-8 w-8 bg-navy text-white rounded-full flex items-center justify-center font-bold text-sm">2</div>
            <h3 className="text-lg font-bold text-navy">Step 2 of 3: Upload Required Documents</h3>
          </div>

          <div className="space-y-4 max-w-4xl">
            {uploadSlots.map((slot) => (
              <div key={slot.id} className="flex items-center justify-between p-4 border border-border rounded-lg bg-white group hover:border-blue-kserc/50 transition-all shadow-sm">
                <div className="flex items-center gap-4">
                  <div className={`p-2.5 rounded-lg ${slot.file ? 'bg-surplus/10 text-surplus' : 'bg-slate-100 text-slate-400'}`}>
                    <FileText size={20} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-navy flex items-center gap-2">
                      {slot.label}
                      {slot.mandatory && <span className="text-[10px] bg-gap/10 text-gap px-1.5 py-0.5 rounded-sm uppercase tracking-tighter">Required</span>}
                    </div>
                    <div className="text-[12px] text-[#7A8A99] mt-0.5">
                      {slot.file ? slot.file.name : 'No file selected'}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  {slot.file ? (
                    <button 
                      onClick={() => removeFile(slot.id)}
                      className="p-2 text-slate-400 hover:text-gap hover:bg-gap/10 rounded-md transition-all"
                      title="Remove file"
                    >
                      <X size={18} />
                    </button>
                  ) : (
                    <button
                      onClick={() => fileInputRefs.current[slot.id]?.click()}
                      className="bg-white border-2 border-blue-kserc text-blue-kserc text-[12px] font-bold px-4 py-2 rounded hover:bg-blue-kserc hover:text-white transition-all flex items-center gap-2"
                    >
                      <Upload size={14} /> Upload
                    </button>
                  )}
                  <input
                    type="file"
                    ref={el => fileInputRefs.current[slot.id] = el}
                    onChange={(e) => handleFileChange(slot.id, e)}
                    className="hidden"
                    accept=".pdf,.xlsx,.xls"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Step 3 */}
        <div className="p-8 bg-slate-50">
          <div className="flex items-center gap-4 mb-8">
            <div className="h-8 w-8 bg-navy text-white rounded-full flex items-center justify-center font-bold text-sm">3</div>
            <h3 className="text-lg font-bold text-navy">Step 3 of 3: Verify & Submit</h3>
          </div>

          <div className="flex items-center justify-between gap-6 max-w-4xl">
            <div className="text-sm text-[#5A6A7A] leading-relaxed">
              Ensure all mandatory documents (Annual Accounts, ARR Order, and Previous Truing-Up) are uploaded before proceeding. The AI analysis will take approximately 2-3 minutes.
            </div>
            <div className="flex gap-4 shrink-0">
              <button
                onClick={() => {
                  setUploadSlots(prev => prev.map(s => ({ ...s, file: null })));
                  setSelectedLicensee('');
                }}
                className="px-8 py-3 bg-white border border-border text-[#445566] font-bold rounded-md hover:bg-slate-100 transition-all text-sm uppercase tracking-widest"
              >
                Cancel
              </button>
              <button
                onClick={handleRunAnalysis}
                disabled={!isMandatoryUploaded || !selectedLicensee}
                className="px-8 py-3 bg-blue-kserc text-white font-bold rounded-md shadow-lg hover:bg-[#174E8C] disabled:bg-[#A0B4C8] disabled:cursor-not-allowed transition-all uppercase tracking-widest text-sm flex items-center gap-2"
              >
                Run AI Analysis <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

