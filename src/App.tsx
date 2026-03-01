/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from 'react';
import { Page, Licensee, LineItem } from './types';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import UploadAnalyse from './components/UploadAnalyse';
import Analyzing from './components/Analyzing';
import AnalysisResults from './components/AnalysisResults';
import ReasoningDetail from './components/ReasoningDetail';
import ReportGeneration from './components/ReportGeneration';
import HistoricalOrders from './components/HistoricalOrders';
import Benchmarks from './components/Benchmarks';
import Login from './components/Login';

const DEFAULT_LINE_ITEMS: LineItem[] = [
  { 
    name: 'Power Purchase', 
    claimed: 45.2, 
    approved: 45.2, 
    status: 'pass',
    reasoning: 'Verified against PPA rates and SLDC energy accounting. All costs are within approved merit order dispatch.'
  },
  { 
    name: 'Employee Cost', 
    claimed: 12.3, 
    approved: 11.8, 
    status: 'flagged',
    reasoning: 'Claimed amount exceeds normative cap defined in Regulation 12(3). AI recommends disallowing excess of Rs. 0.50L based on AICPI escalation limits.'
  },
  { 
    name: 'R&M Expense', 
    claimed: 3.1, 
    approved: 2.9, 
    status: 'flagged',
    reasoning: 'Repairs and Maintenance expenses are 6% higher than previous year. AI flagged for manual verification of asset capitalization vs maintenance.'
  },
  { 
    name: 'Section 3(1) Duty', 
    claimed: 2.5, 
    approved: 0, 
    status: 'rejected',
    reasoning: 'Statutory duty under Section 3(1) is not a pass-through cost as per KSERC Tariff Regulations 2021. Entire claim is disallowed.'
  },
  { 
    name: 'CSR Expense', 
    claimed: 1.2, 
    approved: 0, 
    status: 'rejected',
    reasoning: 'Corporate Social Responsibility (CSR) expenses must be met from profits and cannot be recovered from consumers through tariff.'
  },
  { 
    name: 'Depreciation', 
    claimed: 8.9, 
    approved: 8.9, 
    status: 'pass',
    reasoning: 'Calculated as per straight-line method using rates specified in Annexure-I of the Regulations. Matches asset register.'
  },
  { 
    name: 'Interest on Loans', 
    claimed: 6.5, 
    approved: 6.5, 
    status: 'pass',
    reasoning: 'Interest rates verified with bank certificates. Weighted average rate of interest matches the normative interest calculation.'
  },
];

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [activePage, setActivePage] = useState<Page>('login');
  const [licensees, setLicensees] = useState<Licensee[]>([]);
  const [lineItems, setLineItems] = useState<LineItem[]>(DEFAULT_LINE_ITEMS);
  const [currentAnalysis, setCurrentAnalysis] = useState<{
    licensee: string;
    year: string;
    lineItem?: string;
  } | null>(null);
  const [completedReports, setCompletedReports] = useState<Record<string, { gap: number, type: 'gap' | 'surplus' }>>({});

  useEffect(() => {
    if (isLoggedIn) {
      fetch('/api/licensees')
        .then(res => res.json())
        .then(data => setLicensees(data))
        .catch(err => console.error('Error fetching licensees:', err));
      setActivePage('dashboard');
    }
  }, [isLoggedIn]);

  const updateLineItem = (name: string, updates: Partial<LineItem>) => {
    setLineItems(prev => prev.map(item => 
      item.name === name ? { ...item, ...updates } : item
    ));
  };

  const handleReportFinalized = (licensee: string, gap: number) => {
    setCompletedReports(prev => ({
      ...prev,
      [licensee]: {
        gap,
        type: gap >= 0 ? 'gap' : 'surplus'
      }
    }));
  };

  const handleClearReport = (licensee: string) => {
    setCompletedReports(prev => {
      const next = { ...prev };
      delete next[licensee];
      return next;
    });
  };

  if (!isLoggedIn) {
    return <Login onLogin={() => setIsLoggedIn(true)} />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#F0F2F5]">
      <Header onLogout={() => setIsLoggedIn(false)} />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar activePage={activePage} onPageChange={setActivePage} />
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-6xl mx-auto">
            {activePage === 'dashboard' && (
              <Dashboard 
                onStartAnalysis={() => setActivePage('upload')} 
                completedReports={completedReports}
                onClearReport={handleClearReport}
              />
            )}
            {activePage === 'upload' && (
              <UploadAnalyse 
                licensees={licensees} 
                onStartAnalysis={(licensee, year) => {
                  setCurrentAnalysis({ licensee, year });
                  setLineItems(DEFAULT_LINE_ITEMS); // Reset for new analysis
                  setActivePage('analyzing');
                }} 
              />
            )}
            {activePage === 'analyzing' && currentAnalysis && (
              <Analyzing 
                licensee={currentAnalysis.licensee} 
                year={currentAnalysis.year} 
                onComplete={() => setActivePage('results')} 
              />
            )}
            {activePage === 'results' && currentAnalysis && (
              <AnalysisResults 
                licensee={currentAnalysis.licensee} 
                year={currentAnalysis.year} 
                lineItems={lineItems}
                onViewReasoning={(item) => {
                  setCurrentAnalysis({ ...currentAnalysis, lineItem: item });
                  setActivePage('reasoning');
                }}
                onGenerateReport={() => setActivePage('reports')}
              />
            )}
            {activePage === 'reasoning' && currentAnalysis && currentAnalysis.lineItem && (
              <ReasoningDetail 
                item={lineItems.find(i => i.name === currentAnalysis.lineItem)!} 
                onUpdate={(updates) => updateLineItem(currentAnalysis.lineItem!, updates)}
                onBack={() => setActivePage('results')} 
              />
            )}
            {activePage === 'reports' && (
              <ReportGeneration 
                licensee={currentAnalysis?.licensee} 
                year={currentAnalysis?.year} 
                lineItems={lineItems}
                onBack={currentAnalysis ? () => setActivePage('results') : undefined}
                onReportFinalized={handleReportFinalized}
              />
            )}
            {activePage === 'history' && <HistoricalOrders />}
            {activePage === 'benchmarks' && <Benchmarks />}
          </div>
        </main>
      </div>
      <footer className="bg-navy text-white/40 text-[11px] text-center py-2 border-t-2 border-gold-kserc flex-shrink-0">
        Kerala State Electricity Regulatory Commission &nbsp;·&nbsp;
        AI Truing-Up Tool &nbsp;·&nbsp; Work Order KSERC/CSO/03-05 &nbsp;·&nbsp;
        Developed by RIET, Thiruvananthapuram &nbsp;·&nbsp; Confidential — Authorised Use Only
      </footer>
    </div>
  );
}

