import { NextRequest, NextResponse } from 'next/server';

const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

export async function POST(req: NextRequest) {
    try {
        const { analysis_id, response: userResponse } = await req.json();

        const response = await fetch(`${PYTHON_BACKEND}/review/${analysis_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ response: userResponse }),
        });

        if (!response.ok) {
            return NextResponse.json(
                { error: 'Review submission failed' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        return NextResponse.json({ error: 'Connection failed' }, { status: 500 });
    }
}
