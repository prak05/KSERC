import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { CheckCircle, Clock } from 'lucide-react';

interface AnalyzingProps {
  licensee: string;
  year: string;
  onComplete: () => void;
}

export default function Analyzing({ licensee, year, onComplete }: AnalyzingProps) {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);

  const steps = [
    'Document Ingestion Complete (4 files)',
    'Revenue & Cost Data Extracted',
    'Revenue Gap Computed: ₹64.72 Lakh',
    'Running Prudence Checks...',
    'Generating Reasoning Report...',
  ];

  const reasoningLogs = [
    '> Loaded KSERC Tariff Regulations 2021',
    '> Employee Cost (Actual ₹12.3L) vs Norm ₹11.8L',
    '> ⚠ Excess of ₹0.5L flagged for review',
    '> Distribution Loss: Actual 2.86% vs Target 4.23%',
    '> Efficiency Gain = (4.23 - 2.86)% × Energy Input',
    '> Licensee retains 2/3 of savings: Calculating...',
    '> Section 3(1) Duty detected: ₹2.5L → Disallowed',
    '> CSR Expense detected: ₹1.2L → Disallowed',
    '> Finalizing draft order...',
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setTimeout(onComplete, 1000);
          return 100;
        }
        return prev + 1;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [onComplete]);

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 2000);

    const logInterval = setInterval(() => {
      setLogs(prev => {
        if (prev.length < reasoningLogs.length) {
          return [...prev, reasoningLogs[prev.length]];
        }
        return prev;
      });
    }, 1500);

    return () => {
      clearInterval(stepInterval);
      clearInterval(logInterval);
    };
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between border-b border-border pb-4">
        <div>
          <h2 className="font-serif text-[21px] font-bold text-navy">Analyzing: {licensee} — {year}</h2>
          <p className="text-[13px] text-[#445566] mt-1">AI engine is processing documents and applying regulatory logic</p>
        </div>
        <div className="text-[12px] text-[#7A8A99]">
          <span className="text-blue-kserc">Home</span> › Analyzing
        </div>
      </div>

      <div className="bg-white border border-border rounded-lg shadow-sm overflow-hidden p-8">
        <div className="max-w-3xl mx-auto space-y-10">
          <div className="space-y-6">
            {steps.map((step, idx) => (
              <div key={idx} className="flex items-center gap-4">
                {idx < currentStep ? (
                  <CheckCircle className="text-surplus" size={20} />
                ) : idx === currentStep ? (
                  <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }}>
                    <Clock className="text-blue-kserc" size={20} />
                  </motion.div>
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-border" />
                )}
                <span className={`text-sm font-medium ${idx < currentStep ? 'text-surplus' : idx === currentStep ? 'text-blue-kserc font-bold' : 'text-[#7A8A99]'}`}>
                  {step}
                </span>
                {idx === currentStep && (
                  <div className="flex-1 ml-4">
                    <div className="h-1.5 bg-border rounded-full overflow-hidden">
                      <motion.div 
                        className="h-full bg-blue-kserc"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="space-y-3">
            <h4 className="text-[11px] font-bold text-navy uppercase tracking-widest">AI Reasoning Log</h4>
            <div className="bg-navy p-6 rounded-lg font-mono text-[12px] text-[#A8C0D8] space-y-1.5 h-64 overflow-y-auto shadow-inner">
              {logs.map((log, idx) => (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                >
                  {log}
                </motion.div>
              ))}
              <motion.div 
                animate={{ opacity: [1, 0] }}
                transition={{ repeat: Infinity, duration: 0.8 }}
                className="inline-block w-2 h-4 bg-blue-kserc ml-1 align-middle"
              />
            </div>
          </div>

          <p className="text-center text-sm text-[#7A8A99] italic">
            Please wait. Do not close this window.
          </p>
        </div>
      </div>
    </div>
  );
}
