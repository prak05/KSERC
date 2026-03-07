import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import fs from 'fs';
import path from 'path';

export async function GET(req: NextRequest) {
    try {
        const { searchParams } = new URL(req.url);
        const caseId = searchParams.get('caseId');

        if (!caseId) return NextResponse.json({ error: 'Missing caseId' }, { status: 400 });

        if (caseId === 'all') {
            const DB_PATH = path.join(process.cwd(), '.local-db.json');
            if (!fs.existsSync(DB_PATH)) return NextResponse.json({ cases: [] });

            const rawData = fs.readFileSync(DB_PATH, 'utf8');
            const data = JSON.parse(rawData);
            const savedCases = data.truing_cases
                .filter((c: any) => c.status === 'SAVED' || c.status === 'COMPLETED' || c.status === 'analysis_done' || c.status === 'PARTIAL')
                .map((c: any) => ({
                    ...c,
                    licensees: data.licensees.find((l: any) => l.id === c.licensee_id)
                }))
                .sort((a: any, b: any) => b.created_at.localeCompare(a.created_at));

            return NextResponse.json({ cases: savedCases });
        }

        const cData = db.getCase(caseId);
        const chData = db.getCostHeads(caseId);
        const revData = db.getRevenueData(caseId);

        return NextResponse.json({ cData, chData, revData });
    } catch (error: any) {
        console.error("Get Results Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
