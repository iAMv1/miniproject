// MindPulse — Supabase Edge Function: chat (Gemini proxy)
//
// POST /functions/v1/chat  { message, history?: [{role, content}] }
// Streams/returns a Gemini response with a stress-supportive system prompt.
// Set GEMINI_API_KEY in the function secrets.

const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "*" };

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS },
  });
}

const GEMINI_KEY = Deno.env.get("GEMINI_API_KEY") ?? "";
const MODEL = "gemini-flash-latest";

// ── Authorization: verify JWT signature + require role=authenticated.
//    (verify_jwt alone passes the anon key — it is a valid signed JWT.)
function b64urlToBytes(s: string): Uint8Array {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4 === 0 ? "" : "=".repeat(4 - (b64.length % 4));
  const bin = atob(b64 + pad);
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

async function isAuthenticatedUser(req: Request): Promise<boolean> {
  const auth = req.headers.get("Authorization") ?? "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
  if (!token) return false;
  const secret = Deno.env.get("SUPABASE_JWT_SECRET");
  if (!secret) return false;
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  try {
    const key = await crypto.subtle.importKey(
      "raw", new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" }, false, ["verify"],
    );
    const valid = await crypto.subtle.verify(
      "HMAC", key, b64urlToBytes(parts[2]),
      new TextEncoder().encode(`${parts[0]}.${parts[1]}`),
    );
    if (!valid) return false;
    const payload = JSON.parse(new TextDecoder().decode(b64urlToBytes(parts[1])));
    return payload.role === "authenticated" && Boolean(payload.sub);
  } catch {
    return false;
  }
}

const SYSTEM = `You are MindPulse's supportive wellness assistant. Keep answers
short, warm and practical. You help users understand stress signals, suggest
concrete micro-breaks, and never diagnose or give medical advice. If the user
mentions severe distress, gently suggest professional support.`;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "86400",
      },
    });
  }
  if (req.method !== "POST") {
    return new Response("method not allowed", { status: 405, headers: CORS });
  }
  if (!(await isAuthenticatedUser(req))) {
    return json({ error: "unauthorized" }, 401);
  }
  if (!GEMINI_KEY) {
    return json({ error: "GEMINI_API_KEY not configured" }, 503);
  }
  try {
    const { message, history = [] } = await req.json();
    if (!message) {
      return json({ error: "message required" }, 400);
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
      return json({ error: `Gemini ${res.status}: ${err.slice(0, 200)}` }, 502);
    }
    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    return json({ reply: text });
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
});


