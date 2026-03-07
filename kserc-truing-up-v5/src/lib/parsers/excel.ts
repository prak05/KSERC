import * as XLSX from 'xlsx';

export async function extractTextFromExcelBuffer(buffer: Buffer): Promise<string> {
    try {
        const workbook = XLSX.read(buffer, { type: 'buffer' });
        let fullText = '';

        // Extract text from all sheets
        for (const sheetName of workbook.SheetNames) {
            const worksheet = workbook.Sheets[sheetName];
            const csv = XLSX.utils.sheet_to_csv(worksheet);
            fullText += `\\n--- Sheet: ${sheetName} ---\\n${csv}`;
        }

        return fullText;
    } catch (error) {
        console.error("Excel Parsing failed:", error);
        throw new Error("Failed to parse Excel document.");
    }
}
