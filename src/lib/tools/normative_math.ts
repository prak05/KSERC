/**
 * KSERC SDL Truing Up — Deterministic Math Tools
 * 
 * Pure-TypeScript functions implementing KSERC regulatory formulas.
 * These must be called by agents; the LLM must NEVER perform arithmetic itself.
 * 
 * All monetary values are in Rs. Lakhs unless stated otherwise.
 */

export function calculateDistributionLossPenalty(
    actualLossPct: number,
    targetLossPct: number,
    totalUnitsPurchasedMu: number,
    avgCostPerUnit: number
): { excessLossPct: number; excessUnitsMu: number; penaltyRsLakhs: number } {
    if (actualLossPct <= targetLossPct) {
        return {
            excessLossPct: 0.0,
            excessUnitsMu: 0.0,
            penaltyRsLakhs: 0.0,
        };
    }

    const excessLossPct = actualLossPct - targetLossPct;
    const excessUnitsMu = totalUnitsPurchasedMu * (excessLossPct / 100.0);
    const penaltyRsLakhs = excessUnitsMu * 10.0 * avgCostPerUnit;

    return {
        excessLossPct: Number(excessLossPct.toFixed(4)),
        excessUnitsMu: Number(excessUnitsMu.toFixed(6)),
        penaltyRsLakhs: Number(penaltyRsLakhs.toFixed(4)),
    };
}

export function calculateOmEscalation(
    baseYearCost: number,
    cpiCurrent: number,
    cpiPrevious: number,
    wpiCurrent: number,
    wpiPrevious: number
): {
    cpiEscalation: number;
    wpiEscalation: number;
    blendedEscalation: number;
    normativeCapRsLakhs: number;
} {
    if (cpiPrevious === 0.0 || wpiPrevious === 0.0) {
        throw new Error("Previous CPI/WPI cannot be zero.");
    }

    const cpiEsc = (cpiCurrent - cpiPrevious) / cpiPrevious;
    const wpiEsc = (wpiCurrent - wpiPrevious) / wpiPrevious;
    const blended = 0.70 * cpiEsc + 0.30 * wpiEsc;
    const normativeCap = baseYearCost * (1.0 + blended);

    return {
        cpiEscalation: Number(cpiEsc.toFixed(6)),
        wpiEscalation: Number(wpiEsc.toFixed(6)),
        blendedEscalation: Number(blended.toFixed(6)),
        normativeCapRsLakhs: Number(normativeCap.toFixed(4)),
    };
}

export function calculateRevenueGapSurplus(
    totalApprovedRevenue: number,
    totalApprovedExpenditure: number
): { revenueGapSurplusRsLakhs: number; position: "surplus" | "gap" } {
    const gapSurplus = totalApprovedRevenue - totalApprovedExpenditure;
    const position = gapSurplus >= 0 ? "surplus" : "gap";

    return {
        revenueGapSurplusRsLakhs: Number(gapSurplus.toFixed(4)),
        position,
    };
}

export function calculateInterestOnNormativeLoan(
    approvedCapex: number,
    equityRatio: number = 0.30,
    interestRate: number = 0.08
): { normativeLoanRsLakhs: number; interestRsLakhs: number } {
    const loanPortion = 1.0 - equityRatio;
    const normativeLoan = approvedCapex * loanPortion;
    const interest = normativeLoan * interestRate;

    return {
        normativeLoanRsLakhs: Number(normativeLoan.toFixed(4)),
        interestRsLakhs: Number(interest.toFixed(4)),
    };
}

export function imputeSurplusInterest(
    accumulatedSurplus: number,
    sbiDepositRate: number
): { imputedInterestRsLakhs: number } {
    if (accumulatedSurplus <= 0) {
        return { imputedInterestRsLakhs: 0.0 };
    }

    const interest = accumulatedSurplus * sbiDepositRate;
    return { imputedInterestRsLakhs: Number(interest.toFixed(4)) };
}
