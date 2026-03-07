import { NextRequest, NextResponse } from 'next/server';
import {
    computeDeviation, computeAllowedAmount, computeARR,
    computeRevenueGap, revenueCheckPasses, energyBalanceCheck,
    classifyDeviation, computeDeterministicAllowedAmount
} from '@/lib/formulas';
import { callLLM, KSERC_SYSTEM_PROMPT, buildPrudencePrompt } from '@/lib/llm';
import { retrieveContext } from '@/lib/rag';
import { db } from '@/lib/db';
import fs from 'fs';
import path from 'path';

// Pre-load custom knowledge base rules if available
let customRulesText = '';
try {
    const rulesPath = path.join(process.cwd(), 'src/data/rules.json');
    if (fs.existsSync(rulesPath)) {
        const rules = JSON.parse(fs.readFileSync(rulesPath, 'utf8'));
        customRulesText = `\n\nCRITICAL KNOWLEDGE BASE GUIDELINES:\nNew Rules: ${rules.new_rules}\nTariff Data: ${rules.tariff_data}\nHistorical Precedents: ${rules.historical_data}\n`;
    }
} catch (e) {
    console.error('Failed to load rules.json', e);
}

export async function POST(req: NextRequest) {
    try {
        const { caseId, aicpi, licenseeName } = await req.json();

        // 1. Load case data from Local DB
        const caseData = db.getCase(caseId);
        if (!caseData) throw new Error("Case not found");

        const costHeads = db.getCostHeads(caseId);
        const revenueData = db.getRevenueData(caseId);

        if (!costHeads?.length || !revenueData) throw new Error("Missing financial data");

        const licName = licenseeName || caseData.licensees?.name || 'Local Licensee';

        // 2. Validate revenue data
        const computedRevenue = (revenueData.units_sold_mu * revenueData.avg_tariff_per_unit) / 10;
        const revenueOk = revenueCheckPasses(revenueData.reported_revenue_cr, computedRevenue);

        const energyCheck = energyBalanceCheck(
            revenueData.energy_input_mu,
            revenueData.distribution_loss_pct,
            revenueData.units_sold_mu
        );

        // 3. Process each cost head
        const results = [];
        for (const head of costHeads) {
            const { delta, deltaPct } = computeDeviation(Number(head.approved_cr), Number(head.actual_cr));
            const flagLevel = classifyDeviation(deltaPct, delta);

            let aiVerdict = 'approved';
            let aiAllowedCr = Number(head.actual_cr);
            let aiReason = 'Within normative limits — fully approved.';
            let aiOrderRef = '';

            const deterministicResult = computeDeterministicAllowedAmount(
                head.head_name,
                Number(head.actual_cr),
                Number(head.approved_cr),
                caseData,
                revenueData
            );

            const needsPrudenceCheck = flagLevel === 'critical' || flagLevel === 'moderate' || deterministicResult.isDeterministic;

            if (needsPrudenceCheck) {
                const ragQuery = `${licName} ${head.head_name} deviation ${Math.round(deltaPct)}%`;
                let ragContext = "";
                try {
                    ragContext = await retrieveContext(ragQuery, 3);
                } catch (e) { }

                // Inject the /rules knowledge base
                if (customRulesText) {
                    ragContext += customRulesText;
                }

                const prudencePrompt = buildPrudencePrompt(
                    licName,
                    head.head_name,
                    Number(head.approved_cr),
                    Number(head.actual_cr),
                    deltaPct,
                    ragContext,
                    deterministicResult.mathDetails,
                    deterministicResult.allowed
                );
                let rawResponse: string = '';
                try {
                    rawResponse = await callLLM(KSERC_SYSTEM_PROMPT, prudencePrompt, 800);
                } catch (llmCallErr: unknown) {
                    console.warn('LLM call failed, falling back to formula:', llmCallErr);
                    if (deterministicResult.isDeterministic && deterministicResult.allowed !== null) {
                        aiVerdict = deterministicResult.allowed < Number(head.actual_cr) ? 'partial' : 'approved';
                        aiAllowedCr = deterministicResult.allowed;
                        aiReason = `Mathematical formula fallback due to LLM error: ${deterministicResult.mathDetails}`;
                    } else {
                        const formulaResult = computeAllowedAmount(Number(head.approved_cr), Number(head.actual_cr), head.head_name, aicpi);
                        aiVerdict = formulaResult.verdict;
                        aiAllowedCr = formulaResult.allowed;
                        aiReason = `Formula fallback due to LLM error for ${head.head_name}.`;
                    }
                    rawResponse = '';
                }
                if (rawResponse) {
                    try {
                        const parsedStr = rawResponse.replace(/```json|```/g, '').trim();
                        const parsed = JSON.parse(parsedStr);

                        const scratchpad = parsed.step_by_step_reasoning ? parsed.step_by_step_reasoning.join(" ") : "";
                        console.log(`[${head.head_name} LLM Scratchpad]:`, scratchpad);

                        aiVerdict = parsed.verdict.toLowerCase().replace(' ', '_');
                        aiAllowedCr = parsed.allowed_cr;
                        // Use original reasoning, but keep scratchpad in logs.
                        aiReason = parsed.reasoning;
                        aiOrderRef = parsed.order_reference;

                        // Enforce math limits even if LLM hallucinated
                        if (deterministicResult.isDeterministic && deterministicResult.allowed !== null) {
                            if (Math.abs(aiAllowedCr - deterministicResult.allowed) > 0.02) {
                                console.warn(`Mathematical override for ${head.head_name}: LLM chose ${aiAllowedCr}, overriding to ${deterministicResult.allowed}. LLM Scratchpad was: ${scratchpad}`);
                                aiAllowedCr = deterministicResult.allowed;
                                aiVerdict = aiAllowedCr < Number(head.actual_cr) ? 'partial' : 'approved';
                            }
                        }
                    } catch (llmErr: unknown) {
                        console.error('LLM JSON parse failed, using formula fallback', llmErr);
                        if (deterministicResult.isDeterministic && deterministicResult.allowed !== null) {
                            aiVerdict = deterministicResult.allowed < Number(head.actual_cr) ? 'partial' : 'approved';
                            aiAllowedCr = deterministicResult.allowed;
                            aiReason = `Mathematical formula fallback after parse error: ${deterministicResult.mathDetails}`;
                        } else {
                            const formulaResult = computeAllowedAmount(Number(head.approved_cr), Number(head.actual_cr), head.head_name, aicpi);
                            aiVerdict = formulaResult.verdict;
                            aiAllowedCr = formulaResult.allowed;
                            aiReason = `Formula fallback after JSON parse error for ${head.head_name}.`;
                        }
                    }
                }
            } else {
                if (deterministicResult.isDeterministic && deterministicResult.allowed !== null) {
                    aiVerdict = deterministicResult.allowed < Number(head.actual_cr) ? 'partial' : 'approved';
                    aiAllowedCr = deterministicResult.allowed;
                    aiReason = `Applied strictly based on KSERC structural formulae. Detail: ${deterministicResult.mathDetails}`;
                } else {
                    const formulaResult = computeAllowedAmount(Number(head.approved_cr), Number(head.actual_cr), head.head_name, aicpi);
                    aiVerdict = formulaResult.verdict;
                    aiAllowedCr = formulaResult.allowed;
                }
            }

            const updateData = {
                deviation_pct: deltaPct,
                flag_level: flagLevel || null,
                ai_verdict: aiVerdict,
                ai_allowed_cr: aiAllowedCr,
                ai_reason: aiReason,
                ai_order_reference: aiOrderRef,
                final_verdict: aiVerdict,
                final_allowed_cr: aiAllowedCr,
            };
            db.updateCostHead(head.id, updateData);

            results.push({ ...head, deltaPct, flagLevel, aiVerdict, aiAllowedCr, aiReason });
        }

        // 4. Compute ARR and Revenue Gap
        const arrActual = computeARR(results.map(r => r.aiAllowedCr));
        const revenueGap = computeRevenueGap(arrActual, Number(revenueData.reported_revenue_cr));

        // 5. Update case with computed totals
        db.updateCase(caseId, {
            actual_arr_cr: arrActual,
            revenue_actual_cr: revenueData.reported_revenue_cr,
            revenue_gap_cr: revenueGap,
            status: 'analysis_done',
            updated_at: new Date().toISOString(),
        });

        return NextResponse.json({
            success: true,
            arrActual,
            revenueGap,
            flagsRaised: results.filter(r => r.flagLevel).length,
            revenueCheckOk: revenueOk,
            energyBalanceOk: energyCheck.valid,
        });
    } catch (error: unknown) {
        console.error('Analysis Error:', error);
        return NextResponse.json({ error: error instanceof Error ? error.message : "Unknown error" }, { status: 500 });
    }
}
