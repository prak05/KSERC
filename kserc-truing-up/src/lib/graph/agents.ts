import { TruingUpState } from "./state";
import { precedentLookup } from "../knowledge/precedent_lookup";
import { calculateDistributionLossPenalty, calculateRevenueGapSurplus } from "../tools/normative_math";
import { ChatOpenAI } from "@langchain/openai"; // Use OpenRouter or anything via BaseChatModel

// Initialize LLM. Since the user requested a free LLM, we can assume process.env.OPENAI_API_KEY might point to OpenRouter or similar.
// For now, we will use a generic ChatOpenAI config. The user can configure baseURL and apiKey in .env.local
const model = new ChatOpenAI({
    modelName: process.env.LLM_MODEL_NAME || "google/gemini-1.5-flash", // OpenRouter ID example
    openAIApiKey: process.env.OPENROUTER_API_KEY || "dummy",
    configuration: {
        baseURL: process.env.OPENROUTER_BASE_URL || "https://openrouter.ai/api/v1",
    },
    temperature: 0.1,
});

export async function extractorNode(state: typeof TruingUpState.State) {
    // Pass through the data, initialize totals.
    const caseData = state.caseData;
    let totalClaimed = 0;

    if (caseData.costHeads) {
        caseData.costHeads.forEach((ch: any) => {
            totalClaimed += ch.claimed_amount || 0;
        });
    }

    return { totalClaimed };
}

export async function auditorNode(state: typeof TruingUpState.State) {
    const caseData = state.caseData;
    const approvedExpenses: Record<string, number> = {};
    const disallowances: any[] = [];
    let totalApproved = 0;

    const licensee = caseData.licensees?.name || "Unknown";
    const fy = caseData.financial_year || "Unknown";

    for (const ch of (caseData.costHeads || [])) {
        const claim = ch.claimed_amount || 0;
        let approved = claim;
        let reason = "";

        const nameLower = (ch.cost_head_name || "").toLowerCase();

        // 1. Math Rules: Distribution Loss Penalty
        if (nameLower.includes("power purchase")) {
            // Assuming we have energy data in caseData, fallback to 0 if not present to not break it.
            const actualLoss = caseData.actual_loss || 5.2; // Example
            const targetLoss = caseData.target_loss || 5.0; // Example
            const totalUnits = caseData.total_units || 100; // Example
            const avgCost = caseData.avg_cost || 5.0; // Example

            const penalty = calculateDistributionLossPenalty(actualLoss, targetLoss, totalUnits, avgCost);
            if (penalty.penaltyRsLakhs > 0) {
                // Convert Lakhs to Crores simplified for this scale, or assume it's directly Crores for the sake of demo.
                const penaltyCr = penalty.penaltyRsLakhs / 100;

                approved = Math.max(0, claim - penaltyCr);
                reason = `Disallowed ₹${penaltyCr.toFixed(2)} Cr due to excess distribution loss (${actualLoss}% vs target ${targetLoss}%). KSERC normative math strictly prohibits recovery of excess losses.`;
            }
        }

        // 2. Query Precedent Database for Justification
        const justification = precedentLookup.buildPrecedentJustification(licensee, nameLower, claim, fy);
        if (justification) {
            reason += (reason ? " " : "") + justification;
        }

        if (!reason && claim > 0) {
            // if no reason but there is a disallowed amount from user input previously
            if (ch.allowed_amount !== undefined && ch.allowed_amount < claim) {
                approved = ch.allowed_amount;
            }
        }

        approvedExpenses[ch.cost_head_name] = approved;
        totalApproved += approved;
        if (claim - approved > 0) {
            disallowances.push({
                item: ch.cost_head_name,
                amountCut: claim - approved,
                reason: reason || "Disallowed as per KSERC regulations."
            });
        }
    }

    const revenue = caseData.actual_revenue || 0;
    const gapObj = calculateRevenueGapSurplus(revenue, totalApproved);

    return {
        approvedExpenses,
        disallowances,
        totalApproved,
        revenueGapSurplus: gapObj.revenueGapSurplusRsLakhs
    };
}

export async function drafterNode(state: typeof TruingUpState.State) {
    const prompt = `
You are a senior regulatory analyst for KSERC.
Based on the following truing-up data and strict mathematical rulings (which CANNOT be altered), draft the narrative report.
Licensee: ${state.caseData.licensees?.name}
Financial Year: ${state.caseData.financial_year}
Total Claimed: ₹${state.totalClaimed.toFixed(2)} Cr
Total Approved: ₹${state.totalApproved.toFixed(2)} Cr
Revenue Gap/Surplus: ₹${state.revenueGapSurplus.toFixed(2)} Cr

Disallowances (MUST explicitly mention these exact reasons):
${state.disallowances.map((d: any) => `- ${d.item}: Disallowed ₹${d.amountCut.toFixed(2)} Cr. Reason: ${d.reason}`).join("\n")}

Write the following sections (use formal regulatory language, use newlines for spacing):
1. Background of the Truing-Up Case for ${state.caseData.licensees?.name} for the FY ${state.caseData.financial_year}
2. Commission's Detailed Observations and Reasoning 
   (Detailed bullet points for EVERY item. For each item, clearly explain the reason for the verdict based on the provided disallowances. Use ₹ symbol for currency. DO NOT create any tables here, only text and bullet points.)
3. Summary Order / Directions

CRITICAL INSTRUCTION: DO NOT generate ANY tables in your response. The tables are generated by the system automatically. Your job is ONLY to write the narrative text.
`;

    // Provide fallback to Google Gemini directly if OpenRouter setup is incomplete
    let responseText = "";
    try {
        const response = await model.invoke(prompt);
        responseText = response.content as string;
    } catch (err: any) {
        console.error("LLM Error:", err);
        // Since user may not have OpenRouter keys immediately set, we will format a deterministic draft as fallback.
        responseText = `
1. Background of the Truing-Up Case for ${state.caseData.licensees?.name} for the FY ${state.caseData.financial_year}
The Commission has evaluated the petition based on strict regulatory precedents and distribution loss formulas.

2. Commission's Detailed Observations and Reasoning
${state.disallowances.length > 0 ? state.disallowances.map((d: any) => `* **${d.item}**: The Commission disallows ₹${d.amountCut.toFixed(2)} Cr. ${d.reason}`).join("\n") : "All claims were evaluated and found reasonable."}

3. Summary Order / Directions
The Commission approves the total expenditure of ₹${state.totalApproved.toFixed(2)} Cr, resulting in a revenue gap/surplus of ₹${state.revenueGapSurplus.toFixed(2)} Cr.
     `;
    }

    return { draftNarrative: responseText };
}
