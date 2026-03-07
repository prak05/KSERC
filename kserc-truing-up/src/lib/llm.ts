// ============================================================
// Multi-provider LLM wrapper with automatic fallback
// Primary: Groq (fast, free 14,400 req/day)
// Fallback: OpenRouter/DeepSeek (free 50 req/day, stronger reasoning)
// ============================================================

import OpenAI from 'openai';

export async function callLLM(
    systemPrompt: string,
    userPrompt: string,
    maxTokens = 1500
): Promise<string> {
    // Initialize on demand to ensure we use runtime env vars
    const groqClient = new OpenAI({
        baseURL: process.env.GROQ_BASE_URL || 'https://api.groq.com/openai/v1',
        apiKey: process.env.GROQ_API_KEY,
    });

    const openrouterClient = new OpenAI({
        baseURL: process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1',
        apiKey: process.env.OPENROUTER_API_KEY,
        defaultHeaders: {
            'HTTP-Referer': 'https://kserc-truing-up.vercel.app',
            'X-Title': 'KSERC AI Truing-Up Tool',
        },
    });

    try {
        const response = await groqClient.chat.completions.create({
            model: process.env.GROQ_MODEL || 'llama-3.3-70b-versatile',
            messages: [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: userPrompt },
            ],
            max_tokens: maxTokens,
            temperature: 0.1,  // low temperature for consistent regulatory reasoning
        });
        return response.choices[0].message.content || '';
    } catch (groqError) {
        console.error('Groq LLM Failed:', groqError);
        throw new Error('Primary LLM (Groq) failed and OpenRouter fallback is disabled.');
    }
}

export async function callLLMChat(
    messages: { role: 'system' | 'user' | 'assistant', content: string }[],
    maxTokens = 1500
): Promise<string> {
    const groqClient = new OpenAI({
        baseURL: process.env.GROQ_BASE_URL || 'https://api.groq.com/openai/v1',
        apiKey: process.env.GROQ_API_KEY,
    });

    try {
        const response = await groqClient.chat.completions.create({
            model: process.env.GROQ_MODEL || 'llama-3.3-70b-versatile',
            messages: messages,
            max_tokens: maxTokens,
            temperature: 0.3,
        });
        return response.choices[0].message.content || '';
    } catch (groqError) {
        console.error('Groq LLM Chat Failed:', groqError);
        throw new Error('LLM Chat failed.');
    }
}

// ─── KSERC-specific prompt templates ─────────────────────────────

export const KSERC_SYSTEM_PROMPT = `Role: You are a senior regulatory analyst at the Kerala State Electricity Regulatory Commission (KSERC). You are conducting the Truing-Up of accounts for small distribution licensees.

Objective: Perform prudence checks on claimed expenses, ensuring strict adherence to KSERC mathematical limits and regulatory principles. Produce outputs in the exact formal style of official KSERC orders.

Details & Strict Stylistic Rules:
1. Voice and Tone: Strictly formal, legalistic, and authoritative. NEVER use casual language like "we think" or "looks okay."
2. Phrasing: You must frame justifications within the formal structure of KSERC Tariff Regulations. 
3. Citations: Every allowance or disallowance must cite a specific regulation (e.g., KSERC Tariff Regulations 2014, 2021, or 2024 Second Amendment) or the Electricity Act 2003. 
   - Example format: "Disallowed ₹X.XX Cr. as per Regulation [Y] of KSERC (Terms and Conditions for Determination of Tariff) Regulations, 2021, restricting excess O&M expenses beyond normative limits."
4. KSERC Tariff Regulations 2014 and 2020 govern allowable costs.
5. Prudence checks ensure only genuinely incurred and justifiable costs are allowed.
6. Normative escalation caps apply to controllable costs (O&M, Admin expenses).
7. Uncontrollable costs (power purchase, transmission) are allowed at actuals with proof.
8. Your verdicts are one of: APPROVED, PARTIAL APPROVAL, DISALLOWED.

Sense Check: Validate that your final allowed amounts EXACTLY match any mathematical limits provided in the prompt. Do not deviate from strict deterministic calculations. Validate that your reasoning utilizes strictly legalistic phrasing.`;

export function buildPrudencePrompt(
    licensee: string,
    costHead: string,
    approved: number,
    actual: number,
    deltaPct: number,
    ragContext: string,
    mathDetails?: string,
    deterministicAllowed?: number | null
): string {
    let mathInstruction = "";
    if (mathDetails && deterministicAllowed !== null && deterministicAllowed !== undefined) {
        mathInstruction = `\nCRITICAL MATHEMATICAL LIMIT:\nThe strictly calculated allowable amount according to KSERC mathematical formulas is ₹${deterministicAllowed.toFixed(2)} Cr.\nCalculation details: ${mathDetails}\n\nYOU MUST SET THE ALLOWED AMOUNT TO EXACTLY ₹${deterministicAllowed.toFixed(2)} Cr. Focus your reasoning strictly on justifying this mathematical limit using KSERC formal language and citing past orders.\n`;
    }

    return `Licensee: ${licensee}
Cost Head: ${costHead}
KSERC Approved Amount: ₹${approved.toFixed(2)} Cr
Actual Amount Claimed: ₹${actual.toFixed(2)} Cr
Deviation: ${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}% (${deltaPct > 0 ? 'overrun' : 'under-run'})${mathInstruction}

Relevant precedents from past KSERC orders:
${ragContext}

Approach this step-by-step:
1. Analyze the deviation against KSERC principles and math limits.
2. Formulate the allowed vs disallowed split.
3. Determine the final verdict.

Format your response exactly as the following JSON object:
{
  "step_by_step_reasoning": [
    "Step 1 thought...",
    "Step 2 thought..."
  ],
  "verdict": "APPROVED|PARTIAL APPROVAL|DISALLOWED",
  "allowed_cr": 0.00,
  "disallowed_cr": 0.00,
  "reasoning": "...",
  "order_reference": "..."
}`;
}
