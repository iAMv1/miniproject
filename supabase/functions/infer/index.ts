// MindPulse — Supabase Edge Function: stress inference (Deno)
//
// Scores the XGBoost model (JSON, tree-walker — no Python needed).
// Model JSON is fetched from the Storage bucket 'models' at cold start
// (upload frontend/public/models/xgb_model.json there) and cached.
//
// POST /functions/v1/infer  { features: {23 keys} }
// Returns: score, deviation_level (OK|ELEVATED), stress_probability,
//          level, probabilities, timestamp
//
// Honest semantics: binary deviation vs baseline threshold (40 default);
// universal 3-class accuracy measured ≈ chance — this output is the
// defensible one.

const MODEL_URL = Deno.env.get("MODEL_JSON_URL")
  ?? "https://supabase.storage.supabase.co/placeholder"; // set to your bucket URL

const FEATURES = [
  "hold_time_mean", "hold_time_std", "hold_time_median",
  "flight_time_mean", "flight_time_std", "typing_speed_wpm",
  "error_rate", "pause_frequency", "pause_duration_mean",
  "burst_length_mean", "rhythm_entropy", "mouse_speed_mean",
  "mouse_speed_std", "direction_change_rate", "click_count",
  "rage_click_count", "scroll_velocity_std", "tab_switch_freq",
  "switch_entropy", "session_fragmentation", "hour_of_day",
  "day_of_week", "session_duration_min",
];
const NUM_CLASS = 3;
const THRESHOLD_MILD = 40;
const THRESHOLD_HIGH = 70;

let cached: any = null;

async function loadModel() {
  if (cached) return cached;
  const res = await fetch(MODEL_URL, { headers: { "Cache-Control": "max-age=86400" } });
  if (!res.ok) throw new Error(`model fetch failed: ${res.status}`);
  cached = await res.json();
  return cached;
}

function softmax(v: number[]) {
  const mx = Math.max(...v);
  const e = v.map((x) => Math.exp(x - mx));
  const s = e.reduce((a, b) => a + b, 0);
  return e.map((x) => x / s);
}

function scoreOne(x: number[], model: any): number[] {
  const gb = model.learner.gradient_booster.model;
  const trees = gb.trees;
  const baseScore = JSON.parse(
    model.learner.learner_model_param.base_score,
  );
  const margin = baseScore.slice();
  for (let t = 0; t < trees.length; t++) {
    const cls = t % NUM_CLASS;
    const tree = trees[t];
    const left = tree.left_children;
    const right = tree.right_children;
    const splitIdx = tree.split_indices;
    const splitCond = tree.split_conditions;
    const leaves = tree.base_weights;
    let node = 0;
    while (left[node] !== -1) {
      const f = splitIdx[node];
      node = x[f] < splitCond[node] ? left[node] : right[node];
    }
    margin[cls] += leaves[node];
  }
  return softmax(margin);
}

// Distribution guards identical to the backend: dead features zeroed,
// values clipped to training 1st/99th percentiles.
const CLIP_LO = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
const CLIP_HI = [2000,1500,1500,3000,2500,60,1.5,30,60,60,6,800,600,30,300,40,300,30,3,1,24,7,120];
const ZEROED = new Set([
  "hold_time_mean", "hold_time_std", "hold_time_median",
  "flight_time_mean", "flight_time_std", "pause_frequency",
  "pause_duration_mean", "burst_length_mean", "rhythm_entropy",
  "session_fragmentation", "session_duration_min", "hour_of_day", "day_of_week",
]);

function preprocess(features: Record<string, number>): number[] {
  return FEATURES.map((name, i) => {
    let v = Number(features[name] ?? 0);
    if (ZEROED.has(name)) return 0;
    v = Math.max(CLIP_LO[i], Math.min(CLIP_HI[i], v));
    return v;
  });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
        "Access-Control-Max-Age": "86400",
      },
    });
  }
  if (req.method !== "POST") {
    return new Response("method not allowed", { status: 405 });
  }
  try {
    const { features } = await req.json();
    if (!features || typeof features !== "object") {
      return new Response(JSON.stringify({ error: "features required" }), {
        status: 400, headers: { "Content-Type": "application/json" },
      });
    }
    const x = preprocess(features);
    const model = await loadModel();
    const probs = scoreOne(x, model);
    const score =
      probs[0] * 5.0 + probs[1] * 55.0 + probs[2] * 100.0;
    const level = score >= THRESHOLD_HIGH ? "STRESSED"
      : score >= THRESHOLD_MILD ? "MILD" : "NEUTRAL";
    const deviation_level = score >= THRESHOLD_MILD ? "ELEVATED" : "OK";
    const stress_probability =
      1 / (1 + Math.exp(-0.08 * (score - THRESHOLD_MILD)));
    return new Response(JSON.stringify({
      score: Math.round(score * 10) / 10,
      level,
      deviation_level,
      stress_probability: Math.round(stress_probability * 1000) / 1000,
      probabilities: { NEUTRAL: probs[0], MILD: probs[1], STRESSED: probs[2] },
      timestamp: Date.now() / 1000,
      note: "binary deviation semantics; universal 3-class is not claimed",
    }), { headers: { "Content-Type": "application/json" } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }
});
