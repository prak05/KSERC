import pdfParse from 'pdf-parse';

export async function extractTextFromPDFBuffer(buffer: Buffer): Promise<string> {
    try {
        const data = await pdfParse(buffer);
        return data.text;
    } catch (error) {
        console.error("PDF Parsing failed:", error);
        throw new Error("Failed to parse PDF document.");
    }
}
