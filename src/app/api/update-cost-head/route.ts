import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { computeARR, computeRevenueGap } from "@/lib/formulas";

export async function POST(req: NextRequest) {
    try {
        const { costHeadId, newValue, note, newVerdict } = await req.json();

        if (!costHeadId || newValue === undefined || !note) {
            return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
        }

        // 1. Fetch current cost head
        const costHead = db.getCostHead(costHeadId);
        if (!costHead) throw new Error("Cost head not found");

        const caseId = costHead.case_id;

        // 2. Update cost head
        const updatedReason = `[ADMIN OVERRIDE] ${note}\n\nOriginal AI Reason: ${costHead.ai_reason}`;
        db.updateCostHead(costHeadId, {
            final_allowed_cr: newValue,
            ai_reason: updatedReason,
            final_verdict: newVerdict || costHead.final_verdict
        });

        // 3. Recalculate case totals
        const allHeads = db.getCostHeads(caseId);
        const revData = db.getRevenueData(caseId);

        if (allHeads && revData) {
            const arrActual = computeARR(allHeads.map((h: any) => Number(h.final_allowed_cr)));
            const gap = computeRevenueGap(arrActual, Number(revData.reported_revenue_cr));

            db.updateCase(caseId, {
                actual_arr_cr: arrActual,
                revenue_gap_cr: gap
            });
        }

        return NextResponse.json({ success: true });
    } catch (error: any) {
        console.error("Update Cost Head Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
