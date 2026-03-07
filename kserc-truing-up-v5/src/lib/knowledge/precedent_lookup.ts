import * as precedentData from './precedent_db.json';

export class PrecedentLookup {
    private db: any;

    constructor() {
        this.db = precedentData;
    }

    getLicenseeHistory(licensee: string): any {
        const key = Object.keys(this.db).find(k => k.toLowerCase() === licensee.toLowerCase());
        return key ? this.db[key] : {};
    }

    getComponentHistory(licensee: string, component: string): any[] {
        const history = this.getLicenseeHistory(licensee);
        if (!history) return [];

        const records = [];
        for (const [fy, orderData] of Object.entries(history)) {
            const data = orderData as any;
            const claimedExp = data.claimed_expenses || {};
            const approvedExp = data.approved_expenses || {};
            const meta = data._meta || {};

            const claimed = claimedExp[component] || 0.0;
            const approved = approvedExp[component] || 0.0;
            const cutPct = claimed > 0 ? ((1 - approved / claimed) * 100).toFixed(2) : 0.0;

            let ksercReasoning = "";
            for (const d of (data.key_disallowances || [])) {
                if (d.component === component) {
                    ksercReasoning = d.kserc_reasoning || "";
                    break;
                }
            }

            records.push({
                fy,
                order_ref: meta.order_ref || "",
                claimed,
                approved,
                cut_pct: cutPct,
                kserc_reasoning: ksercReasoning
            });
        }

        // Sort by FY
        return records.sort((a, b) => a.fy.localeCompare(b.fy));
    }

    buildPrecedentJustification(licensee: string, component: string, claimed: number, fy: string): string {
        const history = this.getComponentHistory(licensee, component);
        if (!history || history.length === 0) return "";

        const priorRecords = history.filter(r => r.fy < fy);
        const latest = priorRecords.length > 0 ? priorRecords[priorRecords.length - 1] : history[history.length - 1];

        let justification = `Precedent: In ${licensee} FY ${latest.fy} (${latest.order_ref}), the Commission approved ₹${latest.approved} Lakhs against a claim of ₹${latest.claimed} Lakhs`;

        if (parseFloat(latest.cut_pct) > 0) {
            justification += ` (${latest.cut_pct}% reduction). `;
        } else {
            justification += `. `;
        }

        if (latest.kserc_reasoning) {
            let reasoning = latest.kserc_reasoning;
            if (reasoning.length > 300) reasoning = reasoning.substring(0, 297) + "...";
            justification += `KSERC reasoning: '${reasoning}'. `;
        }

        return justification;
    }
}

export const precedentLookup = new PrecedentLookup();
