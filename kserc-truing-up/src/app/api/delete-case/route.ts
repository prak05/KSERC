import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";

export async function DELETE(req: NextRequest) {
    try {
        const { searchParams } = new URL(req.url);
        const caseId = searchParams.get('caseId');

        if (!caseId) return NextResponse.json({ error: 'Missing caseId' }, { status: 400 });

        db.deleteCase(caseId);

        return NextResponse.json({ success: true });
    } catch (error: any) {
        console.error("Delete Analysis Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
