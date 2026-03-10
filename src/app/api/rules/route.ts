import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const rulesPath = path.join(process.cwd(), 'src/data/rules.json');

export async function GET() {
    try {
        if (!fs.existsSync(rulesPath)) {
            return NextResponse.json({ new_rules: "", tariff_data: "", historical_data: "" });
        }
        const data = fs.readFileSync(rulesPath, 'utf-8');
        return NextResponse.json(JSON.parse(data));
    } catch (e: any) {
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();

        // Ensure data dir exists
        const dir = path.dirname(rulesPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        fs.writeFileSync(rulesPath, JSON.stringify(body, null, 2));
        return NextResponse.json({ success: true });
    } catch (e: any) {
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}
