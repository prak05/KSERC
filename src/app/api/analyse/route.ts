/**
 * v5 API Bridge — /api/analyse
 * ==============================
 * Proxies PDF upload + metadata to the Python FastAPI backend at :8000/analyze.
 * Returns { analysis_id } that the frontend polls via /api/status/[id].
 */
import { NextRequest, NextResponse } from 'next/server';

const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();

        // Forward the multipart form directly to Python backend
        const response = await fetch(`${PYTHON_BACKEND}/analyze`, {
            method: 'POST',
            body: formData,
            // Don't set Content-Type — fetch will set multipart boundary automatically
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('[analyse] Python backend error:', errorText);
            return NextResponse.json(
                { error: `Backend error: ${errorText}` },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error: unknown) {
        console.error('[analyse] Error:', error);
        return NextResponse.json(
            { error: error instanceof Error ? error.message : 'Unknown error' },
            { status: 500 }
        );
    }
}
