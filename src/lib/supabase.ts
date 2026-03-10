import { createClient } from "@supabase/supabase-js";

// Initialize the Supabase client.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

// This is the public client for use in both browser and server
export const supabase = createClient(supabaseUrl, supabaseKey);

// This is the admin client for use ONLY in server-side API routes to bypass RLS
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
export const supabaseAdmin = serviceRoleKey
    ? createClient(supabaseUrl, serviceRoleKey, {
        auth: {
            autoRefreshToken: false,
            persistSession: false
        }
    })
    : supabase;
