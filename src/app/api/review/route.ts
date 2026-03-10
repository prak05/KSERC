import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    try {
        const { analysis_id, response: reviewResponse } = await req.json();

        const response = await fetch(`http://localhost:8000/review/${analysis_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ response: reviewResponse }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Review submission failed');
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error: any) {
        console.error('Proxy Review Error:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
