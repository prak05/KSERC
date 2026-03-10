import { NextRequest, NextResponse } from 'next/server';
import { extractTextFromPDFBuffer } from '@/lib/parsers/pdf';
import { extractTextFromExcelBuffer } from '@/lib/parsers/excel';
import { runOcrFallbackChain } from '@/lib/parsers/ocrChain';
import { callLLM } from '@/lib/llm';

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();
        const files = formData.getAll('file') as File[];
        const licensee = formData.get('licensee') as string;
        const fy = formData.get('fy') as string;

        if (!files || files.length === 0) {
            return NextResponse.json({ error: 'No files provided' }, { status: 400 });
        }

        let allExtractedText = '';

        for (const file of files) {
            const buffer = Buffer.from(await file.arrayBuffer());
            const ext = file.name.split('.').pop()?.toLowerCase();

            let text = '';
            // If the file is a PDF or an Image, route it through the Vision/OCR Fallback Chain
            if (ext === 'pdf' || ['png', 'jpg', 'jpeg', 'webp'].includes(ext || '')) {
                text = await runOcrFallbackChain(buffer, file.type);
            } else if (ext === 'xlsx' || ext === 'xls') {
                text = await extractTextFromExcelBuffer(buffer);
            }

            // Limit text chunk size per file to avoid massive token usage in one go.
            // E.g., slicing to roughly 20-30 pages of text.
            allExtractedText += `\\n--- Document: ${file.name} ---\\n${text.substring(0, 150000)}`;
        }

        const systemPrompt = `You are an expert financial extractor. Extract financial truing-up data for the licensee ${licensee} for FY ${fy} from the provided text.
    
Return a well-formatted JSON with two keys: "costHeads" and "revenueData".
costHeads is an array of objects: { name: string, category: "fixed"|"variable"|"roe", approved_cr: number, actual_cr: number }.
Common cost heads: "Power Purchase Cost", "Transmission Charges", "Employee Costs", "O&M Expenses", "Admin & General Expenses", "Depreciation", "Return on Equity", "Interest on Loans".
revenueData is an object: { units_sold_mu: number, avg_tariff_per_unit: number, reported_revenue_cr: number, energy_input_mu: number, distribution_loss_pct: number }.

CRITICAL RULES:
- All money values MUST be in Crore Rupees (₹ Cr). Convert Lakhs to Crores (divide by 100).
- If a value is missing, return 0.
- Return ONLY valid JSON, no markdown blocks.`;

        const rawResponse = await callLLM(systemPrompt, allExtractedText, 1500);

        // Clean markdown formatting if present
        const cleanJson = rawResponse.replace(/```json|```/g, '').trim();
        const parsed = JSON.parse(cleanJson);

        if (parsed.costHeads && Array.isArray(parsed.costHeads)) {
            parsed.costHeads = parsed.costHeads.filter((ch: any) => ch.approved_cr !== 0 || ch.actual_cr !== 0);
        }

        return NextResponse.json({ success: true, data: parsed });
    } catch (error: unknown) {
        console.error('Extraction Error:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 });
    }
}
