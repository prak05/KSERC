import OpenAI from "openai";

/**
 * Extracts raw text using OpenRouter's vision models.
 * Fallback to deepseek or llama vision models.
 */
export async function extractWithOpenRouterVision(
    fileBuffer: Buffer,
    mimeType: string
): Promise<string> {
    const apiKey = process.env.OPENROUTER_API_KEY;
    if (!apiKey || apiKey === "your_openrouter_key" || apiKey.trim() === "") {
        throw new Error("Missing valid OPENROUTER_API_KEY");
    }

    const openrouterClient = new OpenAI({
        baseURL: process.env.OPENROUTER_BASE_URL || "https://openrouter.ai/api/v1",
        apiKey: apiKey,
        defaultHeaders: {
            "HTTP-Referer": "https://kserc-truing-up.vercel.app",
            "X-Title": "KSERC AI Truing-Up Tool",
        },
    });

    const base64 = fileBuffer.toString("base64");
    const dataUrl = `data:${mimeType};base64,${base64}`;

    const prompt = `
    You are a highly precise document-processing assistant for KSERC.
    Return **only** the plain text content of the supplied image/PDF page. 
    Preserve tables, columns, and line breaks where they appear in the original so numbers align with text.
    Do not add any conversational filler, explanations, markdown formatting, or HTML.
  `;

    const response = await openrouterClient.chat.completions.create({
        model: "google/gemini-2.0-flash-lite-preview-02-05:free",
        messages: [
            {
                role: "user",
                content: [
                    { type: "text", text: prompt },
                    {
                        type: "image_url",
                        image_url: { url: dataUrl },
                    } as any, // bypassing strict types for newer visual object schema
                ],
            },
        ],
        max_tokens: 1500,
        temperature: 0.1,
    });

    return response.choices[0].message.content || "";
}
