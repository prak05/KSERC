import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();

        // Proxy to FastAPI
        const response = await fetch('http://localhost:8000/analyze', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'FastAPI Analysis Failed');
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error: any) {
        console.error('Proxy Analysis Error:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
