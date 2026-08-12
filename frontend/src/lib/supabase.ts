/** MindPulse — Supabase client (Supabase-only backend) */
import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export const supabase = createClient(url, anon);

/** Run inference via the Supabase Edge Function (JS tree-walker model). */
export async function inferStress(features: Record<string, number>) {
  const { data, error } = await supabase.functions.invoke("infer", {
    body: { features },
  });
  if (error) throw error;
  return data;
}

/** Chat via the Supabase Edge Function (Gemini proxy). */
export async function chatWithAssistant(message: string, history: { role: string; content: string }[] = []) {
  const { data, error } = await supabase.functions.invoke("chat", {
    body: { message, history },
  });
  if (error) throw error;
  return data;
}
