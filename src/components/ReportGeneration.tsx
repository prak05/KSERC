import { useState, useEffect } from 'react';
import { FileText, Download, CheckCircle, Loader2, ArrowLeft, Search, Eye, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { LineItem } from '../types';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface ReportGenerationProps {
  licensee?: string;
  year?: string;
  lineItems?: LineItem[];
  onBack?: () => void;
  onReportFinalized?: (licensee: string, gap: number) => void;
}

export default function ReportGeneration({ licensee, year, lineItems, onBack, onReportFinalized }: ReportGenerationProps) {
  const [isGenerating, setIsGenerating] = useState(!!licensee);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const totalClaimed = lineItems?.reduce((acc, item) => acc + item.claimed, 0) || 0;
  const totalApproved = lineItems?.reduce((acc, item) => acc + item.approved, 0) || 0;
  const revenueGap = totalClaimed - totalApproved;

  const pastReports = [
    { id: 1, licensee: 'Infoparks Kerala', year: '2024-25', date: '2026-03-01', status: 'Completed' },
    { id: 2, licensee: 'KDHPCL', year: '2023-24', date: '2025-05-12', status: 'Completed' },
    { id: 3, licensee: 'Technopark', year: '2023-24', date: '2025-04-20', status: 'Completed' },
    { id: 4, licensee: 'CSEZA', year: '2022-23', date: '2024-06-15', status: 'Completed' },
  ];

  useEffect(() => {
    if (licensee) {
      const timer = setTimeout(() => {
        setIsGenerating(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [licensee]);

  const handleDownloadPDF = (l?: string, y?: string) => {
    const targetLicensee = l || licensee || 'Unknown';
    const targetYear = y || year || 'Unknown';
    const targetItems = l ? [
      { name: 'Power Purchase', claimed: 45.2, approved: 45.2, status: 'pass' },
      { name: 'Employee Cost', claimed: 12.3, approved: 11.8, status: 'flagged' },
      { name: 'R&M Expense', claimed: 3.1, approved: 2.9, status: 'flagged' },
      { name: 'Depreciation', claimed: 8.9, approved: 8.9, status: 'pass' },
    ] as LineItem[] : (lineItems || []);
    
    setIsDownloading(true);
    
    setTimeout(() => {
      const doc = new jsPDF();
      
      // Header
      doc.setFontSize(16);
      doc.setTextColor(10, 30, 60); // Navy
      doc.text('KERALA STATE ELECTRICITY REGULATORY COMMISSION', 105, 20, { align: 'center' });
      
      doc.setFontSize(10);
      doc.setTextColor(100, 100, 100);
      doc.text('KPFC BHAVANAM, C.V. RAMAN PILLAI ROAD, VELLAYAMBALAM, THIRUVANANTHAPURAM', 105, 27, { align: 'center' });
      
      doc.setDrawColor(10, 30, 60);
      doc.setLineWidth(0.5);
      doc.line(20, 32, 190, 32);
      
      // Title
      doc.setFontSize(14);
      doc.setTextColor(0, 0, 0);
      doc.setFont('helvetica', 'bold');
      doc.text('TRUING-UP ORDER', 105, 45, { align: 'center' });
      
      // Details
      doc.setFontSize(11);
      doc.setFont('helvetica', 'normal');
      doc.text(`Licensee: ${targetLicensee}`, 20, 55);
      doc.text(`Financial Year: ${targetYear}`, 20, 62);
      doc.text(`Order Date: ${new Date().toLocaleDateString('en-IN')}`, 140, 55);
      
      // Summary Table
      const tClaimed = targetItems.reduce((acc, item) => acc + item.claimed, 0);
      const tApproved = targetItems.reduce((acc, item) => acc + item.approved, 0);
      const gap = tClaimed - tApproved;

      autoTable(doc, {
        startY: 70,
        head: [['Particulars', 'Claimed (Lakh)', 'Approved (Lakh)']],
        body: [
          ...targetItems.map(item => [item.name, `Rs. ${item.claimed.toFixed(2)}`, `Rs. ${item.approved.toFixed(2)}`]),
          [{ content: 'Total ARR', styles: { fontStyle: 'bold' } }, 
           { content: `Rs. ${tClaimed.toFixed(2)}`, styles: { fontStyle: 'bold' } }, 
           { content: `Rs. ${tApproved.toFixed(2)}`, styles: { fontStyle: 'bold' } }]
        ],
        theme: 'striped',
        headStyles: { fillColor: [10, 30, 60] },
      });

      const finalY = (doc as any).lastAutoTable.finalY || 150;

      // AI Reasoning Section
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      doc.text('AI Reasoning & Prudence Check:', 20, finalY + 15);
      
      let currentY = finalY + 22;
      targetItems.forEach((item) => {
        if (currentY > 270) {
          doc.addPage();
          currentY = 20;
        }
        
        doc.setFontSize(10);
        doc.setFont('helvetica', 'bold');
        doc.text(`${item.name}:`, 20, currentY);
        
        doc.setFont('helvetica', 'normal');
        const reason = item.reasoning || 'No specific reasoning provided.';
        const splitReason = doc.splitTextToSize(reason, 160);
        doc.text(splitReason, 30, currentY + 5);
        
        currentY += (splitReason.length * 5) + 8;
      });

      // Conclusion
      if (currentY > 250) {
        doc.addPage();
        currentY = 20;
      }
      
      doc.setFontSize(12);
      doc.setFont('helvetica', 'bold');
      doc.text('Commission\'s Directive:', 20, currentY + 10);
      
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      const directiveText = `The Commission approves a final Revenue Gap of Rs. ${gap.toFixed(2)} Lakh for the period under review. This amount shall be carried forward to the next tariff period as per the prevailing regulations. The licensee is directed to adjust the revenue gap in the subsequent tariff filings.`;
      const splitText = doc.splitTextToSize(directiveText, 170);
      doc.text(splitText, 20, currentY + 17);

      // Signature
      const sigY = currentY + 50 > 270 ? 270 : currentY + 50;
      doc.setFontSize(11);
      doc.setFont('helvetica', 'bold');
      doc.text('By Order of the Commission', 140, sigY);
      doc.setFontSize(9);
      doc.setFont('helvetica', 'italic');
      doc.text('(Digitally Signed)', 140, sigY + 5);
      doc.setFontSize(11);
      doc.setFont('helvetica', 'bold');
      doc.text('Secretary, KSERC', 140, sigY + 10);

      doc.save(`KSERC_Order_${targetLicensee.replace(/\s+/g, '_')}_${targetYear}.pdf`);
      
      if (onReportFinalized && !l) {
        onReportFinalized(targetLicensee, gap);
      }

      setIsDownloading(false);
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    }, 1000);
  };

  const reportItems = [
    'Table 1: Comparison of Approved ARR vs Actuals',
    'Table 2: Consumer Mix & Revenue Summary',
    'Table 3: Cost Validation (Line-by-Line)',
    'Table 4: Distribution Loss & Efficiency Analysis',
    'Prudence Check Summary (Rejections & Approvals)',
    'AI Reasoning Appendix (Traceability)',
    `Final Revenue Gap: ₹ ${revenueGap.toFixed(2)} Lakh`,
  ];

  if (!licensee) {
    return (
      <div className="space-y-8">
        <div className="flex items-start justify-between border-b border-border pb-4">
          <div>
            <h2 className="font-serif text-[21px] font-bold text-navy">Generated Reports</h2>
            <p className="text-[13px] text-[#445566] mt-1">Access and download previously generated truing-up reports</p>
          </div>
          <div className="text-[12px] text-[#7A8A99]">
            <span className="text-blue-kserc">Home</span> › Reports
          </div>
        </div>

        <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
          <div className="p-6 border-b border-border bg-slate-50 flex items-center justify-between">
            <div className="relative w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7A8A99]" size={16} />
              <input 
                type="text" 
                placeholder="Search reports..." 
                className="w-full pl-10 pr-4 py-2 border border-border rounded-md text-sm focus:outline-none focus:border-blue-kserc"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-navy text-white text-[11px] font-bold uppercase tracking-widest">
              <tr>
                <th className="px-6 py-3 text-left">Licensee</th>
                <th className="px-6 py-3 text-left">Year</th>
                <th className="px-6 py-3 text-left">Generated Date</th>
                <th className="px-6 py-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {pastReports
                .filter(r => r.licensee.toLowerCase().includes(searchQuery.toLowerCase()))
                .map((report) => (
                <tr key={report.id} className="hover:bg-blue-kserc/5 transition-colors">
                  <td className="px-6 py-4 font-semibold text-navy">{report.licensee}</td>
                  <td className="px-6 py-4 text-[#5A6A7A]">{report.year}</td>
                  <td className="px-6 py-4 text-[#7A8A99] font-mono text-[12px]">{report.date}</td>
                  <td className="px-6 py-4 text-center">
                    <button 
                      onClick={() => handleDownloadPDF(report.licensee, report.year)}
                      className="text-blue-kserc hover:bg-blue-kserc/10 p-2 rounded-md transition-all flex items-center gap-2 mx-auto text-[11px] font-bold uppercase"
                    >
                      <Download size={14} /> Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (isGenerating) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-6">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
        >
          <Loader2 size={48} className="text-blue-kserc" />
        </motion.div>
        <div className="text-center">
          <h3 className="text-lg font-bold text-navy">Compiling Final Report...</h3>
          <p className="text-sm text-[#7A8A99] mt-2">Formatting tables and regulatory citations for {licensee}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          {onBack && (
            <button 
              onClick={onBack}
              className="flex items-center gap-2 text-blue-kserc font-bold text-[11px] uppercase tracking-widest mb-4 hover:underline"
            >
              <ArrowLeft size={14} /> Back to Results
            </button>
          )}
          <h2 className="font-serif text-[21px] font-bold text-navy">Generate Truing-Up Report</h2>
          <p className="text-[13px] text-[#445566] mt-1">{licensee} — {year}</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Reports
        </div>
      </div>

      <div className="max-w-3xl mx-auto">
        {showSuccess && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 bg-surplus/10 border border-surplus/20 text-surplus p-4 rounded-lg flex items-center gap-3"
          >
            <CheckCircle size={20} />
            <span className="text-sm font-bold">Report downloaded successfully!</span>
          </motion.div>
        )}

        <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden">
          <div className="p-8 space-y-8">
            <div className="space-y-4">
              <h3 className="text-[11px] font-bold text-navy uppercase tracking-widest">Report Contents</h3>
              <div className="space-y-3">
                {reportItems.map((item, idx) => (
                  <div key={idx} className="flex items-center gap-3 text-sm text-[#445566]">
                    <CheckCircle size={16} className="text-surplus" />
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4 border-t border-border pt-8">
              <h3 className="text-[11px] font-bold text-navy uppercase tracking-widest">Select Format</h3>
              <div className="grid grid-cols-2 gap-4">
                <label className="flex items-center gap-4 p-4 border border-border rounded-lg cursor-pointer hover:border-blue-kserc transition-all group">
                  <input type="radio" name="format" className="accent-blue-kserc" defaultChecked />
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-red-50 text-red-600 rounded">
                      <FileText size={20} />
                    </div>
                    <div className="text-sm">
                      <div className="font-bold text-navy">PDF Document</div>
                      <div className="text-[11px] text-[#7A8A99]">Official Order Format</div>
                    </div>
                  </div>
                </label>
                <label className="flex items-center gap-4 p-4 border border-border rounded-lg cursor-pointer hover:border-blue-kserc transition-all group">
                  <input type="radio" name="format" className="accent-blue-kserc" />
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-50 text-blue-600 rounded">
                      <FileText size={20} />
                    </div>
                    <div className="text-sm">
                      <div className="font-bold text-navy">Word Document</div>
                      <div className="text-[11px] text-[#7A8A99]">Editable Draft</div>
                    </div>
                  </div>
                </label>
              </div>
            </div>

            <div className="flex gap-4 pt-4">
              <button 
                onClick={() => setShowPreview(true)}
                className="flex-1 px-8 py-4 bg-white border-2 border-blue-kserc text-blue-kserc font-bold rounded-md hover:bg-blue-kserc/5 transition-all text-sm uppercase tracking-widest flex items-center justify-center gap-2"
              >
                <Eye size={18} /> Preview Draft
              </button>
              <button 
                onClick={() => handleDownloadPDF()}
                disabled={isDownloading}
                className="flex-[2] px-8 py-4 bg-blue-kserc text-white font-bold rounded-md shadow-lg hover:bg-[#174E8C] disabled:bg-slate-400 transition-all uppercase tracking-widest text-sm flex items-center justify-center gap-2"
              >
                {isDownloading ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Downloading...
                  </>
                ) : (
                  <>
                    Download Report <Download size={18} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {showPreview && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy/60 backdrop-blur-sm">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white w-full max-w-4xl max-h-[90vh] rounded-xl shadow-2xl overflow-hidden flex flex-col"
            >
              <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-slate-50">
                <h3 className="font-serif text-lg font-bold text-navy">Draft Order Preview</h3>
                <button onClick={() => setShowPreview(false)} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
                  <X size={20} />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-12 bg-[#F8FAFC]">
                <div className="bg-white shadow-lg border border-border p-16 max-w-2xl mx-auto min-h-[800px] font-serif text-[#1C2B3A]">
                  <div className="text-center space-y-2 mb-12">
                    <h1 className="text-xl font-bold uppercase">Kerala State Electricity Regulatory Commission</h1>
                    <p className="text-xs uppercase tracking-widest">KPFC Bhavanam, Vellayambalam, Thiruvananthapuram</p>
                    <div className="h-1 w-24 bg-navy mx-auto mt-4" />
                  </div>

                  <div className="space-y-8">
                    <div className="flex justify-between items-start text-sm">
                      <div className="space-y-1">
                        <p><strong>Licensee:</strong> {licensee}</p>
                        <p><strong>Financial Year:</strong> {year}</p>
                      </div>
                      <p><strong>Date:</strong> {new Date().toLocaleDateString('en-IN')}</p>
                    </div>

                    <div className="text-center">
                      <h2 className="text-lg font-bold underline underline-offset-4">TRUING-UP ORDER</h2>
                    </div>

                    <div className="space-y-4 text-sm leading-relaxed">
                      <p>
                        The Commission, in exercise of the powers conferred on it under Section 61, 62 and 64 of the Electricity Act, 2003 
                        and all other powers enabling it in this behalf, hereby issues the following order on the Truing-up of Accounts 
                        of <strong>{licensee}</strong> for the financial year <strong>{year}</strong>.
                      </p>

                      <div className="space-y-2">
                        <h3 className="font-bold">1. Summary of Aggregate Revenue Requirement (ARR)</h3>
                        <table className="w-full border-collapse border border-border">
                          <thead>
                            <tr className="bg-slate-50">
                              <th className="border border-border p-2 text-left">Particulars</th>
                              <th className="border border-border p-2 text-right">Claimed (₹L)</th>
                              <th className="border border-border p-2 text-right">Approved (₹L)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {lineItems?.map(item => (
                              <tr key={item.name}>
                                <td className="border border-border p-2">{item.name}</td>
                                <td className="border border-border p-2 text-right font-mono">{item.claimed.toFixed(2)}</td>
                                <td className="border border-border p-2 text-right font-mono font-bold">{item.approved.toFixed(2)}</td>
                              </tr>
                            ))}
                            <tr className="bg-slate-50 font-bold">
                              <td className="border border-border p-2">Total ARR</td>
                              <td className="border border-border p-2 text-right font-mono">{totalClaimed.toFixed(2)}</td>
                              <td className="border border-border p-2 text-right font-mono">{totalApproved.toFixed(2)}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>

                      <div className="space-y-4">
                        <h3 className="font-bold">2. AI Reasoning & Prudence Check</h3>
                        <div className="space-y-4">
                          {lineItems?.map(item => (
                            <div key={item.name} className="border-l-2 border-navy pl-4 py-1">
                              <p className="font-bold text-xs uppercase tracking-wider">{item.name}</p>
                              <p className="text-xs text-[#445566] mt-1">{item.reasoning || 'No specific reasoning provided.'}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <h3 className="font-bold">3. Revenue Gap / Surplus</h3>
                        <p>
                          The Commission approves a final Revenue Gap of <strong>₹ {revenueGap.toFixed(2)} Lakh</strong> for the 
                          period under review. This amount shall be carried forward to the next tariff period as per the 
                          prevailing regulations.
                        </p>
                      </div>
                    </div>

                    <div className="pt-12 text-right space-y-1">
                      <p className="font-bold">By Order of the Commission</p>
                      <p className="text-sm italic text-[#7A8A99]">(Digitally Signed)</p>
                      <p className="font-bold">Secretary, KSERC</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border bg-slate-50 flex justify-end gap-3">
                <button onClick={() => setShowPreview(false)} className="px-6 py-2 text-sm font-bold text-[#445566] hover:bg-slate-200 rounded-md transition-all">
                  Close Preview
                </button>
                <button 
                  onClick={() => {
                    setShowPreview(false);
                    handleDownloadPDF();
                  }}
                  className="px-6 py-2 bg-blue-kserc text-white text-sm font-bold rounded-md shadow-md hover:bg-[#174E8C] transition-all flex items-center gap-2"
                >
                  <Download size={16} /> Download Now
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
