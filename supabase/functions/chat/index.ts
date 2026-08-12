// MindPulse — Supabase Edge Function: chat (Gemini proxy)
//
// POST /functions/v1/chat  { message, history?: [{role, content}] }
// Streams/returns a Gemini response with a stress-supportive system prompt.
// Set GEMINI_API_KEY in the function secrets.

const GEMINI_KEY = Deno.env.get("GEMINI_API_KEY") ?? "";
const MODEL = "gemini-flash-latest";

const SYSTEM = `You are MindPulse's supportive wellness assistant. Keep answers
short, warm and practical. You help users understand stress signals, suggest
concrete micro-breaks, and never diagnose or give medical advice. If the user
mentions severe distress, gently suggest professional support.`;

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("method not allowed", { status: 405 });
  }
  if (!GEMINI_KEY) {
    return new Response(JSON.stringify({ error: "GEMINI_API_KEY not configured" }), {
      status: 503, headers: { "Content-Type": "application/json" },
    });
  }
  try {
    const { message, history = [] } = await req.json();
    if (!message) {
      return new Response(JSON.stringify({ error: "message required" }), {
        status: 400, headers: { "Content-Type": "application/json" },
      });
    }
    const contents = [
      { role: "user", parts: [{ text: SYSTEM }] },
      ...history.slice(-8).map((m: any) => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.content }],
      })),
      { role: "user", parts: [{ text: message }] },
    ];
    const body = JSON.stringify({
      contents,
      generationConfig: { maxOutputTokens: 600, temperature: 0.7 },
    });
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${GEMINI_KEY}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body },
    );
    if (!res.ok) {
      const err = await res.text();
      return new Response(JSON.stringify({ error: `Gemini ${res.status}: ${err.slice(0, 200)}` }), {
        status: 502, headers: { "Content-Type": "application/json" },
      });
    }
    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    return new Response(JSON.stringify({ reply: text }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }
});
