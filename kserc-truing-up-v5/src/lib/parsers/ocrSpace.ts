import FormData from "form-data";
import fetch from "node-fetch";

/**
 * Extracts raw text using the OCR.space Free API.
 * Excellent fallback. Requires OCR_SPACE_API_KEY in environment variables.
 */
export async function extractWithOcrSpace(
    fileBuffer: Buffer,
    mimeType: string
): Promise<string> {
    let apiKey = process.env.OCR_SPACE_API_KEY;
    if (!apiKey || apiKey === "your_ocr_space_key" || apiKey.trim() === "") {
        // OCR.space offers a generic free key for testing, but they recommend your own
        apiKey = "helloworld";
    }

    const form = new FormData();
    form.append("file", fileBuffer, {
        filename: "upload." + mimeType.split("/")[1],
        contentType: mimeType,
    });

    form.append("apikey", apiKey);
    form.append("language", "eng");
    form.append("isTable", "true"); // Optimized for KSERC financial tables

    const resp = await fetch("https://api.ocr.space/parse/image", {
        method: "POST",
        body: form,
    });

    const json = await resp.json() as any;
    // OCR.space may return multiple pages
    if (!json.ParsedResults || json.ParsedResults.length === 0) {
        if (json.IsErroredOnProcessing) {
            throw new Error(`OCR.space error: ${json.ErrorMessage.join(', ')}`);
        }
        return "";
    }

    if (json.IsErroredOnProcessing) {
        console.warn(`[OCR.space] Partial error: ${json.ErrorMessage.join(', ')}. Continuing with extracted pages.`);
    }

    const texts = json.ParsedResults.map((r: any) => r.ParsedText).join("\n");
    return texts;
}
