/**
 * v5 API Bridge — /api/review
 * ============================
 * Submits a human approval or override instruction to the Python backend
 * for a job that is AWAITING_REVIEW (LangGraph HITL interrupt).
 *
 * Body: { analysis_id: string, response: string }
 *   response = "Approve"
 *   OR
 *   response = "Allow Rs 56 Lakhs for new Technocity campus"
 */
import { NextRequest, NextResponse } from 'next/server';

const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
    try {
        const { analysis_id, response } = await req.json();

        if (!analysis_id || !response) {
            return NextResponse.json(
                { error: 'analysis_id and response are required' },
                { status: 400 }
            );
        }

        const backendResponse = await fetch(
            `${PYTHON_BACKEND}/review/${analysis_id}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ response }),
            }
        );

        if (!backendResponse.ok) {
            const errorText = await backendResponse.text();
            return NextResponse.json(
                { error: `Backend review error: ${errorText}` },
                { status: backendResponse.status }
            );
        }

        const data = await backendResponse.json();
        return NextResponse.json(data);
    } catch (error: unknown) {
        console.error('[review] Error:', error);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : 'Review submission failed' },
            { status: 500 }
        );
    }
}
