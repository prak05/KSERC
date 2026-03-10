import { NextRequest, NextResponse } from 'next/server';
import { callLLMChat } from '@/lib/llm';
import { db } from '@/lib/db';
import fs from 'fs';
import path from 'path';

export async function POST(req: NextRequest) {
    try {
        const { caseId, messages } = await req.json();

        // 1. Fetch Case Context from Local DB
        const caseData = db.getCase(caseId);
        const costHeads = db.getCostHeads(caseId);

        const costHeadsSummary = costHeads?.map((h: any) =>
            `- ${h.head_name}: Claimed ₹${Number(h.actual_cr).toFixed(2)} Cr, Allowed ₹${Number(h.final_allowed_cr).toFixed(2)} Cr (${h.final_verdict}). Reason context: ${h.ai_reason}`
        ).join('\n') || 'None';

        // 2. Fetch Rules Context
        let rulesContext = "";
        const rulesPath = path.join(process.cwd(), 'src/data/rules.json');
        if (fs.existsSync(rulesPath)) {
            const rulesText = fs.readFileSync(rulesPath, 'utf-8');
            const rulesJson = JSON.parse(rulesText);
            rulesContext = `
NEW RULES / PROVISIONS:
${rulesJson.new_rules?.substring(0, 1500) || 'None'}

TARIFF DATA:
${rulesJson.tariff_data?.substring(0, 1500) || 'None'}

HISTORICAL PRECEDENTS:
${rulesJson.historical_data?.substring(0, 1500) || 'None'}
`;
        }

        // 3. Build System Prompt
        const systemPrompt = `You are the "KSERC Analytical Officer AI". 
You assist human officers in understanding the Truing-Up results for the selected case.
You MUST rely heavily on the KNOWLEDGE BASE provided below. Do not hallucinate regulatory references outside the provided Knowledge Base. Keep responses concise, helpful, and professional.

CASE DETAILS:
Licensee: ${caseData?.licensees?.name || 'Unknown'}
Financial Year: ${caseData?.financial_year || 'Unknown'}
Approved ARR: ₹${caseData?.approved_arr_cr} Cr
Actual Claimed: ₹${costHeads?.reduce((acc: number, cur: any) => acc + Number(cur.actual_cr), 0)} Cr
Actual Allowed: ₹${caseData?.actual_arr_cr} Cr
Gap/Surplus: ₹${caseData?.revenue_gap_cr} Cr
Cost Head Summary:
${costHeadsSummary}

KNOWLEDGE BASE CONTEXT:
${rulesContext}
`;

        // 4. Make LLM Call
        const chatMessages = [
            { role: 'system', content: systemPrompt },
            ...messages.map((m: any) => ({ role: m.role, content: m.content }))
        ];

        const responseText = await callLLMChat(chatMessages);

        return NextResponse.json({ success: true, reply: responseText });
    } catch (e: any) {
        console.error('Chat error:', e);
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}
