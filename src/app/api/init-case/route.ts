import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const { fy, activeLicensee, extractData } = body;

        if (!fy || !activeLicensee) {
            throw new Error('Missing required fields: fy and activeLicensee');
        }

        // 1. Fetch Licensee
        const licensee = db.getLicenseeByShortName(activeLicensee);

        // 2. Create Case
        const caseObj = db.insertCase({
            licensee_id: licensee.id,
            financial_year: fy,
            status: 'draft'
        });

        // 3. Insert Cost Heads
        if (extractData?.data?.costHeads) {
            const heads = extractData.data.costHeads.map((ch: any) => ({
                case_id: caseObj.id,
                head_name: ch.name || ch.head_name,
                category: ch.category,
                approved_cr: ch.approved_cr,
                actual_cr: ch.actual_cr
            }));
            db.insertCostHeads(heads);
        }

        // 4. Insert Revenue Data
        if (extractData?.data?.revenueData) {
            const rev = extractData.data.revenueData;
            db.insertRevenueData({
                case_id: caseObj.id,
                units_sold_mu: rev.units_sold_mu,
                avg_tariff_per_unit: rev.avg_tariff_per_unit,
                reported_revenue_cr: rev.reported_revenue_cr,
                energy_input_mu: rev.energy_input_mu,
                distribution_loss_pct: rev.distribution_loss_pct
            });
        }

        return NextResponse.json({ success: true, caseId: caseObj.id });
    } catch (error: any) {
        console.error("Init Case Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
