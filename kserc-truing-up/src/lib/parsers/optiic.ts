import fetch from "node-fetch";

/**
 * Extracts raw text using the Optiic Free API.
 * An alternative free OCR layer.
 */
export async function extractWithOptiic(
    fileBuffer: Buffer,
    mimeType: string
): Promise<string> {
    const base64Image = fileBuffer.toString("base64");
    const dataUri = `data:${mimeType};base64,${base64Image}`;

    const resp = await fetch("https://api.optiic.dev/v1/ocr", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
        },
        body: JSON.stringify({
            url: dataUri,     // Optiic accepts data URIs in the 'url' field
            language: "eng",
        }),
    });

    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`Optiic failed: ${resp.status} - ${text}`);
    }

    const json = await resp.json() as any;
    if (json.text) {
        return json.text;
    }

    throw new Error("Optiic returned empty text.");
}
