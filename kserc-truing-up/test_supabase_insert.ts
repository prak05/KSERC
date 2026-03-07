import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
);

(async () => {
    try {
        console.log("Fetching licensee...");
        const { data: licRecord, error: licErr } = await supabase
            .from('licensees')
            .select('id')
            .eq('short_name', 'KDHP')
            .single();

        if (licErr) {
            console.error("Licensee fetch error:", licErr);
            return;
        }

        console.log("Inserting case...", licRecord);
        const { data: caseRecord, error: caseErr } = await supabase
            .from('truing_cases')
            .insert({
                licensee_id: licRecord.id,
                financial_year: '2022-23',
                status: 'draft'
            })
            .select('id')
            .single();

        if (caseErr) {
            console.error("Case insert error:", caseErr);
            return;
        }
        console.log("Success! Case ID:", caseRecord.id);

    } catch (e) {
        console.error("Caught exception:", e);
    }
})();
