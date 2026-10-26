# KSERC AI Truing-Up Tool — Design System & Style Guide
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Institution:** Rajadhani Institute of Engineering and Technology  
> **Version:** 1.0 | Date: 2026

---

## 1. Design Philosophy

The KSERC staff are experienced regulatory professionals, predominantly senior in age, who need **zero friction** and **maximum clarity**. The UI must feel like a trusted government instrument — not a startup app.

> **Core Principle:** "Show only what is needed. Speak in the language of the regulator."

### Three Pillars
| Pillar | Meaning |
|---|---|
| **Authority** | Looks official, trustworthy, government-grade |
| **Clarity** | No clutter. One action per screen. Large readable text. |
| **Precision** | Every number is traceable. Every output has a source. |

---

## 2. Color Palette

### Primary Colors
| Name | Hex | Usage |
|---|---|---|
| **KSERC Navy** | `#1A3557` | Primary header, sidebar background, titles |
| **KSERC Blue** | `#2C6FAC` | Buttons (primary), active states, links |
| **Kerala Gold** | `#C8960C` | Accent, KSERC logo strip, key highlights |

### Neutral Colors
| Name | Hex | Usage |
|---|---|---|
| **Page White** | `#F7F8FA` | Page background |
| **Card White** | `#FFFFFF` | Card/panel background |
| **Border Grey** | `#DEE2E8` | Dividers, table borders |
| **Text Primary** | `#1C2B3A` | All body text |
| **Text Secondary** | `#5A6A7A` | Labels, captions, helper text |
| **Text Disabled** | `#9AAABB` | Placeholder text |

### Semantic / Status Colors
| Name | Hex | Usage |
|---|---|---|
| **Surplus Green** | `#1A7F4B` | Approved surplus values |
| **Gap Red** | `#C0392B` | Revenue gap / deficit values |
| **Flagged Amber** | `#D97706` | Anomalies, items needing review |
| **Approved Blue** | `#2563EB` | Commission-approved items |
| **Rejected Grey** | `#6B7280` | Disallowed / rejected items |
| **Info Teal** | `#0891B2` | Informational banners |

---

## 3. Typography

### Font Stack
```
Primary: "Inter", sans-serif          → All UI text
Monospace: "JetBrains Mono", monospace → Financial figures, code
Fallback: system-ui, Arial, sans-serif
```

### Type Scale
| Token | Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| `text-page-title` | 28px | 700 | 1.2 | Page/section title |
| `text-section` | 22px | 600 | 1.3 | Card headers |
| `text-heading` | 18px | 600 | 1.4 | Sub-headings |
| `text-body` | 16px | 400 | 1.6 | Body copy |
| `text-label` | 14px | 500 | 1.4 | Form labels, column headers |
| `text-caption` | 13px | 400 | 1.5 | Helper text, footnotes |
| `text-data` | 15px | 600 | 1.3 | Financial figures (monospace) |
| `text-data-large` | 20px | 700 | 1.2 | Summary KPI values |

> **Accessibility Rule:** Minimum body size is **16px**. Never go below 13px. KSERC staff may include users with reduced visual acuity.

---

## 4. Spacing System (8px Base Grid)
```
4px   → xs  → icon gaps, inline spacing
8px   → sm  → tight component padding
16px  → md  → standard card padding, form field gap
24px  → lg  → section separation inside a card
32px  → xl  → between cards / major sections
48px  → 2xl → page-level vertical rhythm
64px  → 3xl → hero / top section separation
```

---

## 5. Component Styles

### Buttons
```css
/* Primary — Submit / Analyze */
background: #2C6FAC;
color: #FFFFFF;
border-radius: 6px;
padding: 12px 24px;
font-size: 15px;
font-weight: 600;
border: none;
box-shadow: 0 1px 4px rgba(0,0,0,0.15);

/* Secondary — Cancel / Reset */
background: #FFFFFF;
color: #2C6FAC;
border: 1.5px solid #2C6FAC;
border-radius: 6px;
padding: 11px 24px;

/* Danger — Delete / Reject */
background: #C0392B;
color: #FFFFFF;
border-radius: 6px;
padding: 12px 24px;

/* Disabled */
background: #DEE2E8;
color: #9AAABB;
cursor: not-allowed;
```

### Cards / Panels
```css
background: #FFFFFF;
border: 1px solid #DEE2E8;
border-radius: 8px;
box-shadow: 0 1px 3px rgba(0,0,0,0.08);
padding: 24px;
```

### Financial Value Badges
```css
/* Surplus */
background: #DCFCE7; color: #1A7F4B; 
border-radius: 4px; padding: 2px 8px; font-weight: 600;

/* Gap / Deficit */
background: #FEE2E2; color: #C0392B;
border-radius: 4px; padding: 2px 8px; font-weight: 600;

/* Flagged */
background: #FEF3C7; color: #D97706;
border-radius: 4px; padding: 2px 8px; font-weight: 600;
```

### Form Inputs
```css
border: 1.5px solid #DEE2E8;
border-radius: 6px;
padding: 10px 14px;
font-size: 15px;
background: #FFFFFF;
/* Focus: */
border-color: #2C6FAC;
box-shadow: 0 0 0 3px rgba(44,111,172,0.15);
```

### Data Tables
```css
/* Header row */
background: #1A3557; color: #FFFFFF; font-weight: 600; font-size: 14px;

/* Row hover */
background: #EBF3FB;

/* Alternating rows */
even: #F7F8FA; odd: #FFFFFF;

/* Financial column alignment: always right-align numbers */
text-align: right; font-family: "JetBrains Mono";
```

### Alert / Status Banners
```css
/* Info */
background: #E0F2FE; border-left: 4px solid #0891B2; border-radius: 4px; padding: 12px 16px;

/* Warning / Anomaly Detected */
background: #FFFBEB; border-left: 4px solid #D97706;

/* Error / Validation Failed */
background: #FEF2F2; border-left: 4px solid #C0392B;

/* Success / Approved */
background: #F0FDF4; border-left: 4px solid #1A7F4B;
```

---

## 6. Iconography

Use **Heroicons** (MIT license) or **Lucide Icons** — line style only. No filled icons except for status indicators.

| Context | Icon |
|---|---|
| Upload document | `cloud-arrow-up` |
| Analyze / Run | `beaker` or `cpu-chip` |
| Approved | `check-circle` (filled, green) |
| Flagged / Warning | `exclamation-triangle` (filled, amber) |
| Rejected | `x-circle` (filled, red) |
| Report / Download | `document-arrow-down` |
| Historical data | `chart-bar` |
| Settings | `cog-6-tooth` |
| Licensee | `building-office` |
| Financial | `banknotes` |

---

## 7. Layout System

### Page Structure
```
┌─────────────────────────────────────────────────────┐
│  TOPBAR: KSERC Logo | Tool Name | User | Logout      │  64px
├──────────────┬──────────────────────────────────────┤
│              │  PAGE TITLE + BREADCRUMB              │  80px
│   SIDEBAR    ├──────────────────────────────────────┤
│   (240px)    │                                       │
│              │      MAIN CONTENT AREA                │  flex
│   Nav Items  │      max-width: 1200px                │
│              │      padding: 32px                    │
│              │                                       │
└──────────────┴──────────────────────────────────────┘
```

### Sidebar Navigation Items (in order)
1. Dashboard (Home)
2. Upload Documents
3. Analysis — Truing Up
4. Historical Data
5. Reports
6. Settings
7. Help / User Manual

### Responsive Breakpoints
```
Desktop: 1280px+  → Full sidebar + content
Tablet:  768–1279px → Collapsed sidebar (icon-only)
Mobile:  < 768px  → Not a primary target (regulatory tool, desktop use)
```

---

## 8. Data Visualization

For charts and graphs:
- **Library:** Recharts (React) or Chart.js
- **Chart types allowed:** Bar, Line, Gauge — no pie charts (hard to read precisely)
- **Color scheme:** Use palette above (Surplus Green / Gap Red / KSERC Blue)
- **Axes:** Always labeled with units (₹ Lakh, %, Units)
- **Grid lines:** Light (`#DEE2E8`), horizontal only
- **Tooltips:** Always show exact value + year + licensee name

### KPI Summary Cards (Dashboard)
```
┌─────────────────────┐
│  Revenue Gap         │
│  ₹ 64.72 L          │ ← large, monospace, colored red/green
│  FY 2024-25         │ ← caption
│  Infopark Kerala    │ ← sub-caption
└─────────────────────┘
```

---

## 9. Writing & Tone Guidelines

| Situation | Tone Example |
|---|---|
| Success | "Analysis complete. Revenue gap determined: ₹64.72 Lakh." |
| Warning | "Anomaly detected in Employee Cost (FY 2024-25). Review recommended." |
| Error | "Upload failed. Please ensure the file is in PDF or Excel format." |
| Instruction | "Upload the audited accounts for FY 2024-25 to begin." |
| Empty state | "No documents uploaded. Begin by uploading the Annual Accounts." |

> **Voice:** Formal, direct, non-technical jargon. No emojis. No exclamation marks.

---

## 10. Accessibility Requirements

- Minimum contrast ratio: **4.5:1** for body text (WCAG AA)
- All interactive elements must have `:focus` styles
- Font size adjustable via browser zoom (no fixed-pixel overflow)
- Color alone must **never** be the sole indicator of meaning (always accompany with text/icon)
- All form inputs must have associated `<label>` elements
