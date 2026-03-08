import { NextRequest, NextResponse } from 'next/server';

const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

export async function GET(
    req: NextRequest,
    { params }: { params: { id: string } }
) {
    try {
        const { id } = params;
        const response = await fetch(`${PYTHON_BACKEND}/status/${id}`, {
            cache: 'no-store'
        });

        if (!response.ok) {
            return NextResponse.json(
                { error: 'Backend status check failed' },
                { status: response.status }
            );
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        return NextResponse.json({ error: 'Connection failed' }, { status: 500 });
    }
}
