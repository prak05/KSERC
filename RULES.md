# KSERC Truing-Up System — Development Rules

## The Golden Rule

> **Never hardcode a petition-specific value in Python code.**

Every number that belongs to the petition (claimed costs, energy units, loss percentages, 
APPC) must come from:
1. **Gemini extraction** (`extractor.py`) — reading the PDF directly
2. **MYT norms** (`data/myt_baselines/myt_baselines.json`) — regulatory targets from KSERC orders  
3. **Dynamic computation** in the auditor — formula-derived from the above two sources

---

## What Belongs Where

| Value type | Correct source | Example |
|---|---|---|
| Claimed expenses from petition | `extractor.py` → Gemini Vision | `power_purchase_cost = 1023.94` |
| Energy purchased, loss units, APPC | `extractor.py` → Gemini Vision | `energy_purchased = 139.93 LU` |
| MYT-approved expense norms | `myt_baselines.json` | `employee_cost = 24.82` |
| MYT target distribution loss % | `myt_baselines.json` | `target_distribution_loss_pct = 4.23` |
| Approved loss units | **Computed** in auditor | `energy_input × target% / 100` |
| APPC used in audit | **From petition** (Gemini-extracted) | `appc_rs_per_unit = 7.31` |
| PPC efficiency gain/loss | **Computed** in auditor | `(actual_loss - approved_loss) × APPC` |

---

## Rules for `extractor.py`

1. **The Gemini prompt must describe concepts, not locations.**  
   ❌ `"Look for Row 10, Column 'Total'"` — wrong, breaks on different petition formats  
   ✅ `"The actual distribution loss = total input minus total output, in Lakh units"` — correct

2. **Example JSON values in the prompt must be generic/illustrative.**  
   ❌ Using real petition values (6.95, 139.93, 7.31) — Gemini may copy them instead of reading  
   ✅ Use clearly made-up round numbers (8.12, 110.00, 6.50)

3. **Never set a default fallback value for a petition-specific number.**  
   ❌ `actual_loss = state.get("actual_loss_lakh_units", 6.95)` — breaks other petitions  
   ✅ `actual_loss = float(state.get("actual_loss_lakh_units", 0.0) or 0.0)`

4. **`approved_loss_lakh_units` is never extracted from the petition** — return `0.0` always.  
   The petition does not contain this row. The auditor computes it from MYT norms.

---

## Rules for `auditor.py`

1. **Primary source for APPC is always the petition** (`appc_rs_per_unit` from extractor).  
   Only fall back to computing `PPC / energy_purchased` if the petition didn't state it explicitly.  
   Only use MYT norms as a last resort.

2. **Approved loss is always recomputed**, never taken from Gemini or hardcoded:
   ```python
   approved_loss = energy_input_lakh_units × (target_loss_pct / 100)
   ```
   Where:
   - `energy_input_lakh_units` → Gemini-extracted from the Energy Balance table
   - `target_loss_pct` → from `myt_baselines.json`

3. **MYT norms are a ceiling/comparison, not a default fill.**  
   They limit what KSERC approves, but the starting point is always the petition's claimed value.

4. **No `if licensee == "Infopark": value = X` logic.**  
   All licensee-specific parameters must come from `myt_baselines.json` keyed by licensee name.

---

## Rules for `myt_baselines.json`

This file contains **regulatory norms from KSERC MYT Orders** — these are legitimate constants.  
They are NOT petition values and may be stored here.

✅ **Allowed** in `myt_baselines.json`:
- MYT-approved expense limits (employee, R&M, A&G, depreciation, etc.)
- Target distribution loss % per year
- MYT APPC norm (used only as last-resort fallback)
- BEE Energy Audit Fee (fixed regulatory charge)
- Escalation rates (CPI/WPI-based, from KSERC orders)

❌ **Not allowed** in `myt_baselines.json`:
- Actual/claimed values from any specific petition
- Computed results (approved_loss_units, efficiency_gain)
- Any value that should come from Gemini extraction

---

## Rules for Gemini Prompts

1. **Prompts must be format-agnostic.** Different petitions use different table structures.  
   Describe WHAT a value represents, not WHERE it appears in the table.

2. **Do not include petition-specific values** in prompt examples.  
   Example JSON should use round numbers that differ significantly from any real petition.

3. **Unit rules must be stated clearly.**  
   Petitions from Infopark, Technopark, CSEZA use **Lakh units** — state this explicitly.  
   Do NOT instruct Gemini to convert or multiply.

4. **`approved_loss_lakh_units` must always be `0.0` in examples.**  
   This value does not appear in petitions — Gemini should never try to extract it.

---

## Rules for Adding New Licensees

1. Add the licensee's MYT norms to `myt_baselines.json` under the correct name key.
2. Add the `target_distribution_loss_pct` per year from the KSERC MYT Order.
3. Add any licensee-specific aliases to `DEFAULT_TARGET_DIST_LOSS` in `auditor.py` (for name matching).
4. Do NOT add any petition-specific values.

---

## Quick Checklist Before Committing

- [ ] No numeric literals (other than `0.0`, `100`, `1`) in auditor computation logic
- [ ] No petition-specific values in extractor fallback defaults
- [ ] Gemini prompt examples use illustrative numbers only
- [ ] Any new regulatory constants are in `myt_baselines.json`, not in Python code
- [ ] `approved_loss` is always computed, never extracted or hardcoded
- [ ] APPC is from petition first, computed second, MYT norm last
