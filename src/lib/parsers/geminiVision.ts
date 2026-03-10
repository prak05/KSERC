import { GoogleGenerativeAI } from "@google/generative-ai";

/**
 * Extract raw text from an image or PDF page using Gemini Vision.
 * Requires GOOGLE_API_KEY to be set in the environment.
 */
export async function extractWithGemini(file: Buffer, mimeType: string): Promise<string> {
    const apiKey = process.env.GOOGLE_API_KEY;
    if (!apiKey || apiKey === "your_google_ai_studio_key" || apiKey.trim() === "") {
        throw new Error("Missing valid GOOGLE_API_KEY");
    }

    const genAI = new GoogleGenerativeAI(apiKey);
    const model = genAI.getGenerativeModel({ model: process.env.GEMINI_MODEL || "gemini-2.0-flash" });

    const base64 = file.toString("base64");

    const parts = [
        {
            inlineData: {
                mimeType,
                data: base64,
            },
        },
    ];

    const prompt = `
    You are a highly precise document-processing assistant for KSERC.
    Return **only** the plain text content of the supplied image/PDF page. 
    Preserve tables, columns, and line breaks where they appear in the original so numbers align with text.
    Do not add any conversational filler, explanations, markdown formatting, or HTML.
  `;

    const result = await model.generateContent([prompt, ...parts]);
    const response = await result.response;
    return response.text();
}
