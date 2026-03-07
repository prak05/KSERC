/**
 * v5 API Bridge — /api/status/[id]
 * ==================================
 * Polls the Python FastAPI backend for job status.
 * 
 * Returns one of:
 *   { status: "RUNNING" }
 *   { status: "AWAITING_REVIEW", review_summary: { ... } }
 *   { status: "COMPLETED", result: { ... } }
 *   { status: "FAILED", result: { error: "..." } }
 */
import { NextRequest, NextResponse } from 'next/server';

const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

export async function GET(
    _req: NextRequest,
    { params }: { params: { id: string } }
) {
    const { id } = params;
    try {
        const response = await fetch(`${PYTHON_BACKEND}/status/${id}`, {
            cache: 'no-store',
        });

        if (!response.ok) {
            const errorText = await response.text();
            return NextResponse.json(
                { error: `Backend error: ${errorText}` },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error: unknown) {
        console.error('[status] Error:', error);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : 'Poll failed' },
            { status: 500 }
        );
    }
}
