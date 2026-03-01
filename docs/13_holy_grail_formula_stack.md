# KSERC AI Truing-Up — The Holy Grail Document
## Formulas · Math · Tech Stack · Unstoppable AI Architecture
> Work Order KSERC/CSO/03-05 | RIET, Thiruvananthapuram

---

## 1. Core Truing-Up Formula

```
Revenue Gap / Surplus = Approved ARR − Actual Revenue Collected
```
- **Positive result** → Revenue GAP (Commission owes licensee)
- **Negative result** → Revenue SURPLUS (Licensee collected excess)

## 2. AT&C Loss Formula

```
AT&C Loss (%) = [ (Energy Input − Energy Sold) / Energy Input ] × 100
```

## 3. Efficiency Gain Sharing (2/3 Rule)

When Actual AT&C Loss < Approved Target:
- **Efficiency Gain (MU)** = (Target% - Actual%) × Energy Input / 100
- **Power Purchase Savings** = Efficiency Gain (MU) × Power Purchase Cost per Unit
- **Licensee Retains** = (2/3) × Power Purchase Savings
- **Commission Takes** = (1/3) × Power Purchase Savings

## 4. O&M Normative Cap Formula

```
Normative Cap = Previous Year Approved O&M × (1 + Escalation Rate)
```
- **Escalation Rate** = AICPI (All India Consumer Price Index annual change)

## 5. Perennial Rejections (Always ₹0)

1. **Section 3(1) Electricity Duty** → Rejected.
2. **CSR Expenses** → Rejected.
3. **RPO Liability Provisions** → Rejected (only actual REC payments allowed).

---

## Tech Stack (Prototype)

- **Frontend**: React + TypeScript + Tailwind CSS
- **Backend**: Express + Vite (Full-stack)
- **Database**: SQLite (Better-sqlite3)
- **AI**: Google Gemini 1.5 Flash
