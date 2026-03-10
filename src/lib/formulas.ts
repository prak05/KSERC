// ============================================================
// KSERC TRUING-UP FINANCIAL FORMULAS
// All amounts in Crore Rupees (Cr) unless stated otherwise
// All percentages as decimal (0.05 = 5%)
// ============================================================

export interface CostHead {
    name: string;
    category: 'fixed' | 'variable' | 'roe';
    approved: number;    // Approved by KSERC in tariff order (₹ Cr)
    actual: number;      // Actual as per audited accounts (₹ Cr)
}

export interface RevenueData {
    unitsSoldMU: number;     // Million Units sold
    avgTariffPerUnit: number; // ₹ per unit
    reportedRevenue: number; // ₹ Cr as reported by licensee
    energyInputMU: number;   // Total energy input (before losses)
    lossesPercent: number;   // Distribution loss %
}

// ─── 1. Deviation Calculation ─────────────────────────────────────
// Δᵢ = Actual_i − Approved_i
// Δ%ᵢ = (Δᵢ / Approved_i) × 100
export function computeDeviation(approved: number, actual: number) {
    const delta = actual - approved;                    // absolute difference
    const deltaPct = approved !== 0
        ? (delta / approved) * 100                        // percentage deviation
        : actual > 0 ? 100 : 0;                           // handle zero approved
    return { delta, deltaPct };
}

// ─── 2. Prudence Check — Normative Cap ────────────────────────────
// Per KSERC Tariff Regulations, each cost category has a normative escalation cap.
// Expenses beyond the cap are disallowed unless justified with supporting evidence.
export const NORMATIVE_CAPS: Record<string, number> = {
    'O&M Expenses': 0.05,           // 5% escalation allowed over approved
    'Admin & General Expenses': 0.15, // 15% variance allowed
    'Employee Costs': 0.00,          // No escalation — actuals allowed with audit
    'Depreciation': 0.00,            // Per asset schedule — no discretion
    'Return on Equity': 0.00,        // Fixed rate on approved equity base
    'Interest on Loans': 0.00,       // Actual loan interest with agreement
    'Power Purchase Cost': 1.00,     // Full actuals allowed if PPA/KSEB bill provided
    'Transmission Charges': 1.00,    // Full actuals per KSEB transmission billing
};

// Returns the maximum allowed actual for a cost head
// max_allowed = approved × (1 + cap)
export function maxAllowedAmount(approved: number, headName: string, aicpi: number = 4.2): number {
    let cap = NORMATIVE_CAPS[headName] ?? 0.10;       // default 10% cap
    // If O&M, cap is dynamically based on AICPI rate inflation usually. 
    // We'll use the static rule for now or the given AICPI if head is O&M
    if (headName === 'O&M Expenses') {
        cap = aicpi / 100;
    }
    return approved * (1 + cap);                         // e.g. approved=100, cap=0.05 → max=105
}

// ─── 3. Allowed Amount After Prudence Check ────────────────────────
// allowed = min(actual, max_allowed)
// If actual ≤ max_allowed → fully allowed
// If actual > max_allowed → capped at max_allowed (excess disallowed)
export function computeAllowedAmount(
    approved: number,
    actual: number,
    headName: string,
    aicpi: number = 4.2
): { allowed: number; disallowed: number; verdict: string } {
    const max = maxAllowedAmount(approved, headName, aicpi);
    if (actual <= max) {
        return { allowed: actual, disallowed: 0, verdict: 'approved' };
    } else {
        // Exception for unpredictable costs which are usually passed outright
        if (['Power Purchase Cost', 'Transmission Charges'].includes(headName)) {
            return { allowed: actual, disallowed: 0, verdict: 'approved' };
        }
        const allowed = max;
        const disallowed = actual - max;                   // excess amount disallowed
        return { allowed, disallowed, verdict: 'partial' };
    }
}

// ─── 4. Annual Revenue Requirement (ARR) ──────────────────────────
// ARR_actual = Σ(allowed_i) for all cost heads i
export function computeARR(allowedCostHeads: number[]): number {
    return allowedCostHeads.reduce((sum, v) => sum + v, 0); // sum of all allowed costs
}

// ─── 5. Revenue Gap / Surplus ─────────────────────────────────────
// Revenue Gap = ARR_actual − Revenue_actual
// Positive → under-recovery (gap) → licensee's benefit
// Negative → over-recovery (surplus) → to be adjusted in next tariff
export function computeRevenueGap(arrActual: number, revenueActual: number): number {
    return arrActual - revenueActual;                    // positive = gap, negative = surplus
}

// ─── 6. Revenue Cross-Check ────────────────────────────────────────
// Computed Revenue = Units Sold (MU) × Average Tariff (₹/unit) × 10 (to convert to Cr)
export function computeExpectedRevenue(unitsMU: number, tariffPerUnit: number): number {
    return (unitsMU * tariffPerUnit) / 10;               // converts to ₹ Cr
}

// Revenue check passes if computed is within 5% of reported
export function revenueCheckPasses(reported: number, computed: number): boolean {
    if (reported === 0) return true;
    const diff = Math.abs(reported - computed) / reported;
    return diff <= 0.05;                                  // within 5% tolerance
}

// ─── 7. Energy Balance Check ──────────────────────────────────────
// Energy Balance: Input = Sales + Losses
export function energyBalanceCheck(
    inputMU: number,
    lossPercent: number,
    reportedSalesMU: number
): { valid: boolean; expectedSalesMU: number; discrepancyPct: number } {
    const expectedSales = inputMU * (1 - lossPercent / 100); // expected after losses
    const discrepancy = Math.abs(reportedSalesMU - expectedSales);
    const discrepancyPct = inputMU ? (discrepancy / inputMU) * 100 : 0;
    return {
        valid: discrepancyPct <= 2,                         // allow 2% tolerance
        expectedSalesMU: expectedSales,
        discrepancyPct,
    };
}

// ─── 8. Year-on-Year Spike Detection ──────────────────────────────
export function detectYoYSpike(
    current: number,
    prior: number,
    thresholdPct = 20
): { spiked: boolean; growthPct: number } {
    if (prior === 0) return { spiked: false, growthPct: 0 };
    const growthPct = ((current - prior) / prior) * 100;
    return { spiked: growthPct > thresholdPct, growthPct };
}

export function historicalAverageGap(gaps: number[]): number {
    if (gaps.length === 0) return 0;
    return gaps.reduce((sum, g) => sum + g, 0) / gaps.length;
}

// ─── 10. Deviation Flag Level ─────────────────────────────────────
export function classifyDeviation(
    deltaPct: number,
    deltaAbsCr: number
): 'critical' | 'moderate' | 'info' | null {
    const absPct = Math.abs(deltaPct);
    const absVal = Math.abs(deltaAbsCr);
    if (absPct > 25 || absVal > 1) return 'critical';
    if (absPct > 10 || absVal > 0.25) return 'moderate';
    if (absPct > 5) return 'info';
    return null;
}

// ─── 11. Deterministic Mathematical Formulas (from ADWAITH proj) ───

export function calculateDistributionLossPenalty(
    actualLossPct: number,
    targetLossPct: number,
    totalUnitsPurchasedMu: number,
    avgCostPerUnit: number
) {
    if (actualLossPct <= targetLossPct) {
        return {
            excessLossPct: 0.0,
            excessUnitsMu: 0.0,
            penaltyRsCr: 0.0,
        };
    }
    const excessLossPct = actualLossPct - targetLossPct;
    const excessUnitsMu = totalUnitsPurchasedMu * (excessLossPct / 100.0);
    // 1 MU = 10 Lakh units = 0.1 Cr units. 
    // cost is ₹/kWh (or Rs/Unit).
    // Total cost in Cr = excessUnitsMu * 10^6 * avgCostPerUnit / 10^7 = excessUnitsMu * avgCostPerUnit / 10
    const penaltyRsCr = (excessUnitsMu * avgCostPerUnit) / 10.0;

    return {
        excessLossPct,
        excessUnitsMu,
        penaltyRsCr: Number(penaltyRsCr.toFixed(4)),
    };
}

export function calculateOMEscalation(
    baseYearCostCr: number,
    cpiCurrent: number,
    cpiPrevious: number,
    wpiCurrent: number,
    wpiPrevious: number
) {
    if (cpiPrevious === 0 || wpiPrevious === 0) {
        return { blendedEscalation: 0, normativeCapRsCr: baseYearCostCr };
    }
    const cpiEsc = (cpiCurrent - cpiPrevious) / cpiPrevious;
    const wpiEsc = (wpiCurrent - wpiPrevious) / wpiPrevious;
    const blended = 0.70 * cpiEsc + 0.30 * wpiEsc;
    const normativeCap = baseYearCostCr * (1.0 + blended);

    return {
        cpiEscalation: Number(cpiEsc.toFixed(6)),
        wpiEscalation: Number(wpiEsc.toFixed(6)),
        blendedEscalation: Number(blended.toFixed(6)),
        normativeCapRsCr: Number(normativeCap.toFixed(4)),
    };
}

export function calculateRoNFA(
    openingNfaCr: number,
    consumerContributionsCr: number,
    grantsCr: number,
    normativeLoanAssetsCr: number,
    rateOfReturn: number = 0.055
) {
    let eligibleBase = openingNfaCr - consumerContributionsCr - grantsCr - normativeLoanAssetsCr;
    if (eligibleBase < 0) eligibleBase = 0.0;
    const ronfa = eligibleBase * rateOfReturn;

    return {
        eligibleBaseRsCr: Number(eligibleBase.toFixed(4)),
        ronfaRsCr: Number(ronfa.toFixed(4)),
    };
}

export function imputeSurplusInterest(
    accumulatedSurplusCr: number,
    sbiDepositRate: number
) {
    if (accumulatedSurplusCr <= 0) return { imputedInterestRsCr: 0.0 };
    const interest = accumulatedSurplusCr * sbiDepositRate;
    return { imputedInterestRsCr: Number(interest.toFixed(4)) };
}

export function adjustDepreciation(
    claimedDepreciationCr: number,
    depreciationOnGrantFundedAssetsCr: number,
    depreciationOnSurplusFundedAssetsCr: number
) {
    const disallowed = depreciationOnGrantFundedAssetsCr + depreciationOnSurplusFundedAssetsCr;
    const approved = Math.max(claimedDepreciationCr - disallowed, 0.0);
    return {
        disallowedDepreciation: Number(disallowed.toFixed(4)),
        approvedDepreciation: Number(approved.toFixed(4)),
    };
}

export function calculateInterestOnNormativeLoan(
    approvedCapexCr: number,
    equityRatio: number = 0.30,
    interestRate: number = 0.08
) {
    const loanPortion = 1.0 - equityRatio;
    const normativeLoan = approvedCapexCr * loanPortion;
    const interest = normativeLoan * interestRate;
    return {
        normativeLoanRsCr: Number(normativeLoan.toFixed(4)),
        interestRsCr: Number(interest.toFixed(4)),
    };
}

export function calculateDepreciation90PctCap(
    originalCostCr: number,
    accumulatedDepreciationCr: number,
    currentYearDepreciationCr: number
) {
    if (originalCostCr <= 0) {
        return {
            claimedDepreciation: Number(currentYearDepreciationCr.toFixed(4)),
            approvedDepreciationRsCr: 0.0,
            disallowedDepreciationRsCr: Number(currentYearDepreciationCr.toFixed(4)),
            capacityRemainingRsCr: 0.0
        };
    }
    const maxDepreciation = originalCostCr * 0.90;
    const availableDepreciation = maxDepreciation - accumulatedDepreciationCr;

    let approved = 0.0;
    if (availableDepreciation > 0) {
        approved = Math.min(currentYearDepreciationCr, availableDepreciation);
    }
    let disallowed = currentYearDepreciationCr - approved;
    if (disallowed < 0) disallowed = 0.0;

    return {
        claimedDepreciation: Number(currentYearDepreciationCr.toFixed(4)),
        approvedDepreciationRsCr: Number(approved.toFixed(4)),
        disallowedDepreciationRsCr: Number(disallowed.toFixed(4)),
        capacityRemainingRsCr: Number(Math.max(0.0, availableDepreciation - approved).toFixed(4))
    };
}

export function calculateWorkingCapitalInterest(
    omExpensesAnnualCr: number,
    receivablesAnnualCr: number,
    securityDepositsHeldCr: number,
    historicalGfaCr: number = 0.0,
    fuelCostAnnualCr: number = 0.0,
    interestRate: number = 0.09
) {
    const om1Month = omExpensesAnnualCr / 12.0;
    const receivables2Months = (receivablesAnnualCr / 12.0) * 2.0;
    const fuel1Month = fuelCostAnnualCr / 12.0;
    const maintenanceSpares = historicalGfaCr * 0.01;

    let totalWorkingCapital = om1Month + receivables2Months + fuel1Month + maintenanceSpares - securityDepositsHeldCr;
    if (totalWorkingCapital < 0) totalWorkingCapital = 0.0;

    const interest = totalWorkingCapital * interestRate;

    return {
        workingCapitalRsCr: Number(totalWorkingCapital.toFixed(4)),
        interestOnWorkingCapitalRsCr: Number(interest.toFixed(4))
    };
}

// ─── 12. Deterministic Decision Router ───
export function computeDeterministicAllowedAmount(
    headName: string,
    claimedAmountCr: number,
    approvedAmountCr: number,
    caseData: any, // to access FY, licensee, etc.
    revenueData: any // to access MU, load, etc.
) {
    const isOM = ['O&M Expenses', 'Employee Costs', 'Repair & Maintenance', 'Admin & General Expenses'].includes(headName);
    const isPPC = headName === 'Power Purchase Cost';
    const isDepreciation = headName === 'Depreciation';
    const isRoNFA = headName === 'Return on NFA' || headName === 'Return on Equity';
    const isIWC = headName === 'Interest on Working Capital';
    const isLTInterest = headName === 'Interest on Loans' || headName === 'Interest on Long-Term Loans';

    if (isOM) {
        const cap = caseData?.inflation_pct ? (caseData.inflation_pct / 100) : 0.05;
        const maxAllowed = approvedAmountCr * (1 + cap);
        if (claimedAmountCr <= maxAllowed) {
            return { allowed: claimedAmountCr, isDeterministic: true, mathDetails: `Under norm cap of ₹${maxAllowed.toFixed(2)} Cr` };
        } else {
            return { allowed: maxAllowed, isDeterministic: true, mathDetails: `Capped at norm ₹${maxAllowed.toFixed(2)} Cr` };
        }
    }

    if (isPPC) {
        const actualLoss = revenueData?.distribution_loss_pct || 0;
        const targetLoss = caseData?.target_loss_pct || 5.0; // fallback target
        const inputMu = revenueData?.energy_input_mu || 0;
        const avgCost = caseData?.avg_cost_per_unit || 6.0;

        if (actualLoss > targetLoss && inputMu > 0) {
            const result = calculateDistributionLossPenalty(actualLoss, targetLoss, inputMu, avgCost);
            const penalty = result.penaltyRsCr;
            const finalAllowed = Math.max(claimedAmountCr - penalty, 0);
            return {
                allowed: finalAllowed,
                isDeterministic: true,
                mathDetails: `Distribution loss ${actualLoss.toFixed(2)}% > target ${targetLoss.toFixed(2)}%. Penalty: ₹${penalty.toFixed(2)} Cr.`
            };
        }
        return { allowed: claimedAmountCr, isDeterministic: true, mathDetails: 'Actuals allowed (no loss penalty)' };
    }

    if (isDepreciation) {
        const gfaCr = caseData?.gfa_cr || 0;
        if (gfaCr > 0) {
            const mathAllowed = gfaCr * 0.0528; // KSERC 5.28%
            const allowed = Math.min(claimedAmountCr, mathAllowed);
            return {
                allowed,
                isDeterministic: true,
                mathDetails: `Reg 27: 5.28% of eligible GFA (₹${gfaCr} Cr) = ₹${mathAllowed.toFixed(2)} Cr. Allowed min(Claimed, Computed).`
            };
        }
    }

    if (isRoNFA) {
        const nfaCr = caseData?.nfa_cr || 0;
        if (nfaCr > 0) {
            const rate = caseData?.ronfa_rate || 0.055;
            const mathAllowed = nfaCr * rate;
            const allowed = Math.min(claimedAmountCr, mathAllowed);
            return {
                allowed,
                isDeterministic: true,
                mathDetails: `Reg 28: ${(rate * 100).toFixed(1)}% of eligible NFA (₹${nfaCr} Cr) = ₹${mathAllowed.toFixed(2)} Cr.`
            };
        }
    }

    if (isIWC) {
        const omAnn = caseData?.approved_om_cr || (approvedAmountCr * 0.5);
        const revAnn = caseData?.revenue_actual_cr || (revenueData?.reported_revenue_cr || 0);
        const sbiRate = 0.1115; // 11.15% (SBI EBLR 9.15% + 2%)

        const result = calculateWorkingCapitalInterest(omAnn, revAnn, 0, 0, 0, sbiRate);
        const mathAllowed = result.interestOnWorkingCapitalRsCr;
        return {
            allowed: mathAllowed > 0 ? mathAllowed : claimedAmountCr,
            isDeterministic: true,
            mathDetails: `Reg 29: WC logic -> O&M/12 + Receivables/6. Interest @ 11.15% = ₹${mathAllowed.toFixed(2)} Cr.`
        };
    }

    if (headName === 'Section 3(1) Duty' || headName === 'Electricity Duty') {
        return { allowed: 0, isDeterministic: true, mathDetails: 'Statutory rejection under Section 3(1) of Kerala Electricity Duty Act, 1963.' };
    }

    return { allowed: null, isDeterministic: false, mathDetails: '' };
}
