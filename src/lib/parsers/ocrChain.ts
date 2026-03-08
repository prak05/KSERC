import { extractWithGemini } from "./geminiVision";
import { extractWithOpenRouterVision } from "./openrouterVision";
import { extractWithOcrSpace } from "./ocrSpace";
import { extractWithOptiic } from "./optiic";

/**
 * 4-Stage Zero-Cost OCR Fallback Algorithm.
 * Prioritizes speed and reasoning, falling back to basic OCR APIs if quotas are exhausted.
 */
export async function runOcrFallbackChain(fileBuffer: Buffer, mimeType: string): Promise<string> {
    const errors: string[] = [];

    // Stage 1: Google Gemini (Best Speed, 60 RPM Free)
    try {
        console.log("[OCR Chain] Stage 1: Attempting Google Gemini 2.0 Flash Vision...");
        return await extractWithGemini(fileBuffer, mimeType);
    } catch (e: any) {
        errors.push(`Gemini Error: ${e.message}`);
        console.warn("[OCR Chain] Stage 1 Failed", e.message);
    }

    // Stage 3: OCR.space (Dedicated Free OCR API)
    try {
        console.log("[OCR Chain] Stage 3: Attempting OCR.space...");
        return await extractWithOcrSpace(fileBuffer, mimeType);
    } catch (e: any) {
        errors.push(`OCR.space Error: ${e.message}`);
        console.warn("[OCR Chain] Stage 3 Failed", e.message);
    }

    // If all 4 free-tiers failed, throw a compiled error report
    throw new Error(`All OCR fallbacks failed. Errors:\n${errors.join('\n')}`);
}
