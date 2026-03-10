import { NextRequest, NextResponse } from 'next/server';

export async function GET(
    req: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const id = params.id;
        const response = await fetch(`http://localhost:8000/status/${id}`, {
            cache: 'no-store'
        });

        if (!response.ok) {
            throw new Error('Failed to fetch status from FastAPI');
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error: any) {
        console.error('Proxy Status Error:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
