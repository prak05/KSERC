import { createClient } from '@supabase/supabase-js';
import { HfInference } from '@huggingface/inference';

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const historicalCases = [
    {
        licensee: 'KDHP', year: '2019-20', orderNumber: 'KSERC/2020/41',
        approvedArr: 3.21, revenueGap: -0.18, totalDisallowed: 0.08,
        keyRuling: 'O&M overrun of 12% partially disallowed. Employee cost actuals allowed with salary certificates.',
        contentChunk: 'The Commission examined the O&M expenses of KDHP for 2019-20. The actual expenditure of ₹1.24 Cr against approved ₹1.10 Cr represents a 12.7% overrun. Applying normative escalation cap of 5%, the Commission allows ₹1.155 Cr and disallows ₹0.085 Cr as imprudent expenditure.'
    },
    {
        licensee: 'Technopark', year: '2021-22', orderNumber: 'KSERC/2022/18',
        approvedArr: 8.45, revenueGap: 0.62, totalDisallowed: 0.31,
        keyRuling: 'Power purchase cost allowed in full against KSEB bills. Admin expenses disallowed 22% overrun.',
        contentChunk: 'Technopark claimed Admin & General expenses of ₹0.89 Cr against approved ₹0.73 Cr, a deviation of 21.9%. The Commission does not find adequate justification for this overrun and allows only the normative 15% escalation ceiling, allowing ₹0.84 Cr.'
    },
    {
        licensee: 'Infoparks', year: '2022-23', orderNumber: 'KSERC/2023/27',
        approvedArr: 12.10, revenueGap: 1.24, totalDisallowed: 0.55,
        keyRuling: 'Largest revenue gap on record for Infoparks. Transmission charge escalation allowed fully per KSEB billing.',
        contentChunk: 'The Commission notes the revenue gap of ₹1.24 Cr is the highest recorded for Infoparks. The gap is primarily attributable to lower than projected energy consumption by IT tenants following COVID recovery period. The Commission allows the gap to be carried forward as Regulatory Asset to be recovered in future tariff.'
    },
    {
        licensee: 'CSEZA', year: '2020-21', orderNumber: 'KSERC/2021/09',
        approvedArr: 6.83, revenueGap: -0.41, totalDisallowed: 0.22,
        keyRuling: 'Over-recovery due to higher than projected industrial consumption. Surplus adjusted in next tariff order.',
        contentChunk: 'CSEZA recorded revenue surplus of ₹0.41 Cr in 2020-21 due to higher industrial activity. The Commission directs that this surplus shall be adjusted in the approved tariff for 2022-23 by reducing the allowed ARR by equivalent amount.'
    }
];

async function getEmbedding(text: string): Promise<number[]> {
    const hf = new HfInference(process.env.HUGGINGFACE_API_KEY);
    const output = await hf.featureExtraction({
        model: process.env.HF_EMBED_MODEL || 'sentence-transformers/all-MiniLM-L6-v2',
        inputs: text,
    });

    // Convert Float32Array or Nested arrays to simple number array
    const embedding = Array.isArray(output)
        ? (Array.isArray(output[0]) ? output[0] : output)
        : Array.from(output as any);

    return embedding as number[];
}

async function seed() {
    console.log('Seeding knowledge base...');

    for (const item of historicalCases) {
        console.log(`Processing ${item.orderNumber}...`);

        // 1. Get embedding
        const searchString = `${item.licensee} ${item.keyRuling} ${item.contentChunk}`;
        const embedding = await getEmbedding(searchString);

        // 2. Fetch licensee ID
        const { data: licenseeData, error: licError } = await supabase
            .from('licensees')
            .select('id')
            .eq('short_name', item.licensee)
            .single();

        if (licError || !licenseeData) {
            console.log(`Warning: Licensee ${item.licensee} not found, skipping inserting order.`);
            continue;
        }

        // 3. Insert record
        const { error: insertError } = await supabase
            .from('kserc_orders')
            .insert({
                licensee_id: licenseeData.id,
                financial_year: item.year,
                order_number: item.orderNumber,
                order_date: new Date(`20${item.year.split('-')[0]}-04-01`).toISOString(), // Approximated
                approved_arr_cr: item.approvedArr,
                revenue_gap_cr: item.revenueGap,
                total_disallowed_cr: item.totalDisallowed,
                key_ruling: item.keyRuling,
                content_chunk: item.contentChunk,
                embedding: embedding,
            });

        if (insertError) {
            console.error(`Failed to insert ${item.orderNumber}:`, insertError.message);
        } else {
            console.log(`✓ Inserted ${item.orderNumber}`);
        }
    }

    console.log('Knowledge base seeding complete.');
}

seed().catch(console.error);
