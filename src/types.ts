export interface Licensee {
  id: number;
  name: string;
  short_code: string;
}

export interface HistoricalOrder {
  id: number;
  licensee_code: string;
  financial_year: string;
  claimed_lakhs: number | null;
  approved_lakhs: number;
  outcome_type: 'SURPLUS' | 'GAP' | 'REVERSAL' | 'OVERSHOOT';
  notes: string | null;
}

export interface CalculationResult {
  gap_amount: number;
  outcome: 'GAP' | 'SURPLUS';
  is_anomaly: boolean;
  message: string;
}

export interface LineItem {
  name: string;
  claimed: number;
  approved: number;
  status: 'pass' | 'flagged' | 'rejected';
  reasoning?: string;
}

export type Page = 
  | 'login' 
  | 'dashboard' 
  | 'upload' 
  | 'analyzing' 
  | 'results' 
  | 'reasoning' 
  | 'reports' 
  | 'history' 
  | 'benchmarks';
