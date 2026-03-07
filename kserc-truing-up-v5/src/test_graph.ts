import { runTruingUpPipeline } from './lib/graph';

async function test() {
    const sampleCaseData = {
        licensees: { name: "INFOPARK" },
        financial_year: "2024-25",
        actual_loss: 6.0,
        target_loss: 5.0,
        total_units: 100,
        avg_cost: 5.0,
        actual_revenue: 37.22,
        costHeads: [
            {
                cost_head_name: "Power Purchase",
                claimed_amount: 10,
                allowed_amount: 10
            },
            {
                cost_head_name: "Employee Costs",
                claimed_amount: 5,
                allowed_amount: 5
            }
        ]
    };

    try {
        console.log("Starting LangGraph Pipeline...");
        const result = await runTruingUpPipeline(sampleCaseData);

        console.log("=== PIPELINE RESULT ===");
        console.log("Total Claimed:", result.totalClaimed.toFixed(2), "Cr");
        console.log("Total Approved:", result.totalApproved.toFixed(2), "Cr");
        console.log("Revenue Gap/Surplus:", result.revenueGapSurplus.toFixed(2), "Cr");
        console.log("\nDisallowances:");
        result.disallowances.forEach((d: any) => console.log(`- ${d.item}: ₹${d.amountCut.toFixed(2)} Cr (${d.reason})`));

        console.log("\nDraft Narrative:");
        console.log(result.draftNarrative);

    } catch (error) {
        console.error("Test failed:", error);
    }
}

test();
