# KSERC AI Truing-Up Tool — Visual References & Mood Board
> **Project:** AI-Based Analytical Tool for Truing Up of Accounts | Work Order No. KSERC/CSO/03-05  
> **Purpose:** Show-don't-tell references for the "vibe" of this tool. Upload these references to your AI coding assistant.

---

## 1. The Vibe in One Sentence

> **"Indian government regulatory portal meets clean financial dashboard — authoritative, zero clutter, built for bureaucrats."**

---

## 2. Reference Websites (Upload Screenshots to AI)

These are real URLs to visit and screenshot for your AI coding assistant:

### Primary References (Closest Vibe)
| Reference | URL | What to Copy |
|---|---|---|
| CERC (Central Electricity Regulatory Commission) | `https://www.cercind.gov.in/` | Clean government header, sidebar nav, table-heavy content |
| KSERC Official Website | `https://www.erckerala.org/` | Branding, header style, official feel |
| Income Tax e-Filing Portal India | `https://www.incometax.gov.in/` | Login screen, dashboard layout, form design, navy+white palette |
| MCA21 Portal | `https://www.mca.gov.in/` | Table-heavy, formal government portal, minimal decoration |
| UIDAI (Aadhaar) Portal | `https://uidai.gov.in/` | Clean government branding, accessible design, clear typography |

### Dashboard / Financial Reference
| Reference | URL | What to Copy |
|---|---|---|
| Grafana (public demo) | `https://play.grafana.org/` | Data tables, status badges, clean metric cards |
| Metabase (public demo) | `https://www.metabase.com/` | Financial table style, filter bars |
| Retool Templates | `https://retool.com/templates/` | Internal tool aesthetic — functional over decorative |

### What NOT to look like
| Reference | Why to Avoid |
|---|---|
| Dribbble/Behance dashboards | Too stylized, gradients, neon colors — KSERC staff will distrust it |
| Startup SaaS landing pages | Too "marketing-y", not functional |
| Dark mode UIs | Many senior users prefer light mode; avoid dark theme |

---

## 3. Key Visual Design Decisions

### Color Philosophy
```
Think: 
  - The dark navy of an official government letterhead
  - The white of official paper
  - Gold/saffron as an accent (Kerala flag colors)
  - Red for deficits (financial convention)
  - Green for surplus (financial convention)

NOT: 
  - Purple gradients
  - Neon highlights
  - Black backgrounds
  - Pastel pinks or anything decorative
```

### Typography Philosophy
```
Think:
  - Crisp, professional, high-legibility
  - Arial/Inter for general text (universally readable)
  - Monospace font for ALL financial numbers (alignment matters)
  - Large enough for users over 50 years old (base 16px minimum)

NOT:
  - Decorative display fonts
  - Anything below 14px
  - Varied font weights everywhere (2 weights max: regular + bold)
```

### Layout Philosophy
```
Think:
  - Government portal: content first, decoration last
  - Clear visual hierarchy: Page Title → Section → Content
  - Generous padding (the page should breathe)
  - Tables as the primary content type (this IS a data application)
  
NOT:
  - Cards everywhere (too "app-like")
  - Infinite scrolling
  - Animations (except progress bars)
  - Tooltips as the only way to see information
```

---

## 4. Component Mood References

### Login Page Mood
```
Reference: Income Tax e-Filing Portal login
- White card, centered on light blue-grey background
- Logo at top (KSERC + RIET)
- Two inputs, one button
- No background imagery, no gradients
- Bottom text: official identifier (Work Order number)
```

### Dashboard Mood
```
Reference: CERC portal home + Grafana table panels
- Left sidebar with navigation (not icons-only)
- Summary KPI cards at top (3-4 cards max)
- Recent activity list below
- One prominent CTA: "+ Start New Analysis"
- No banner ads, no promotional content, no "upgrade" buttons
```

### Analysis Results Mood
```
Reference: Any Indian regulatory order table
- Think of how an actual KSERC Order looks:
  Table with columns: Particulars | Claimed | Approved | Remarks
- Rows are dense but readable
- Color coded: green row for approved, amber for flagged, red for rejected
- Financial numbers right-aligned in monospace
- "View Reasoning" is a simple text link, not a big button
```

### Report / PDF Mood
```
Reference: Actual KSERC Orders (see uploaded PDF: 20260129161256.pdf)
- KSERC letterhead (logo + official address)
- Title: "ORDER" centered and underlined
- Body: formal regulatory prose
- Tables: numbered (Table 1, Table 2, etc.)
- Footer: "By Order of the Commission" + Secretary
- Black and white; no color other than the logo
```

---

## 5. Anti-Patterns to Avoid (Show These to the AI as "DON'T DO THIS")

```
❌ DO NOT use hero images or background photos
❌ DO NOT use circular avatars or profile pictures anywhere
❌ DO NOT use emoji in the interface (except where explicitly specified)
❌ DO NOT use skeleton loaders (simple "Loading..." text is fine)
❌ DO NOT use confetti animations on "success" states (this is regulatory work, not a game)
❌ DO NOT use gradient buttons or gradient backgrounds
❌ DO NOT use rounded corners on tables (flat borders only)
❌ DO NOT use infinite scroll — pagination only
❌ DO NOT use modals for data entry (use separate pages or inline expansion)
❌ DO NOT use terms like "Awesome!", "Let's go!", or "You're all set!" in the UI
❌ DO NOT use chatbot interfaces (the AI is a background engine, not a chat window)
❌ DO NOT add a dark mode toggle (KSERC didn't ask for it)
```

---

## 6. Prompt Template for Visual Generation

Use this prompt when asking an AI to build a UI screen:

```
Build a [SCREEN NAME] for a government regulatory tool. 

Visual references:
- Style: Indian government portal (like income tax portal or CERC)  
- Color palette: Navy (#1A3557), Blue (#2C6FAC), Gold (#C8960C), white background
- Typography: Inter, 16px base, monospace for financial figures
- Layout: Left sidebar (240px) + main content area
- Tone: Formal, zero decoration, high information density

Specific screen requirements:
[INSERT REQUIREMENTS HERE]

DO NOT use:
- Gradients
- Dark backgrounds
- Decorative fonts
- Animations (except a simple spinner/progress bar)
- Emojis
- Any placeholder text or demo data labels

Use only Tailwind CSS classes. No inline styles.
```
