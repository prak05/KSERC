import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function POST(req: NextRequest) {
    try {
        const { caseId, status } = await req.json();

        if (!caseId) return NextResponse.json({ error: 'Missing caseId' }, { status: 400 });

        db.updateCase(caseId, { status: status || 'SAVED' });

        return NextResponse.json({ success: true });
    } catch (error: any) {
        console.error("Save Analysis Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
