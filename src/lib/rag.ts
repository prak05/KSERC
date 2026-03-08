// ============================================================
// RAG Pipeline: Retrieves relevant past KSERC orders
// for prudence check context
// ============================================================

import { supabase } from './supabase';

// Get embedding for a query text using HuggingFace free API
async function getEmbedding(text: string): Promise<number[]> {
    const response = await fetch(
        `https://router.huggingface.co/hf-inference/models/${process.env.HF_EMBED_MODEL}`,
        {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${process.env.HUGGINGFACE_API_KEY}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ inputs: text, options: { wait_for_model: true } }),
        }
    );

    const data = await response.json();
    if (data.error) throw new Error(data.error);

    // HuggingFace returns array of embeddings for sentence-transformers
    return Array.isArray(data[0]) ? data[0] : data;
}

// Retrieve top-K most similar past order chunks
export async function retrieveContext(
    query: string,
    topK = 5
): Promise<string> {
    try {
        const queryEmbedding = await getEmbedding(query);

        // pgvector cosine similarity search
        const { data, error } = await supabase.rpc('match_kserc_orders', {
            query_embedding: queryEmbedding,
            match_threshold: 0.5,    // minimum cosine similarity
            match_count: topK,
        });

        if (error || !data || data.length === 0) return 'No relevant past orders found.';

        // Format retrieved chunks as numbered list for the LLM
        return data
            .map((row: Record<string, any>, i: number) =>
                `[${i + 1}] Order: ${row.order_number} (${row.order_date.split('T')[0]})\n` +
                `Licensee: ${row.licensee_name} | Year: ${row.financial_year}\n` +
                `Extract: ${row.content_chunk}`
            )
            .join('\n\n');
    } catch (error) {
        console.error("RAG Context Retrieval Failed:", error);
        return 'No relevant past orders found due to an error fetching embeddings.';
    }
}
