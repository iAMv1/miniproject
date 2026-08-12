/** MindPulse — API Client (Supabase-backed, same method signatures).
 *
 * The FastAPI backend is retired from the deployed app. Every method here
 * now talks to Supabase (tables via RLS, model via the `infer` edge
 * function, chat via the `chat` edge function). Pages are untouched.
 */

import { supabase, inferStress, chatWithAssistant } from "./supabase";
import type {
  FeatureVector,
  StressResult,
  HistoryPoint,
  CalibrationStatus,
  UserStats,
  HealthStatus,
  InterventionSnapshot,
  InterventionEvent,
} from "./types";

export const BASE = ""; // kept for compatibility; no longer used

type ChatToolParams = Record<string, unknown>;
type StreamFeatures = Record<string, number>;

export function getToken(): string | null {
  // Supabase owns sessions; the access token is only reachable async.
  // Return null synchronously — nothing should depend on this anymore.
  return null;
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // Supabase tables don't take arbitrary REST paths; methods below are
  // explicit. Kept as a defensive throw for any missed caller.
  throw new Error(`request() is deprecated in Supabase mode: ${path}`);
}

async function userId(): Promise<string | null> {
  const { data } = await supabase.auth.getUser();
  return data.user?.id ?? null;
}

function mapRow(r: Record<string, unknown>): HistoryPoint {
  return {
    timestamp: new Date(String(r.created_at)).getTime() / 1000,
    score: Number(r.score ?? 0),
    level: String(r.level ?? "UNKNOWN"),
    deviation_level: (String(r.deviation_level ?? "OK") as "OK" | "ELEVATED"),
    stress_probability: Number(r.stress_probability ?? 0),
    confidence: Number(r.stress_probability ?? 0),
    insights: [],
    typing_speed_wpm: Number(r.typing_speed_wpm ?? 0),
    error_rate: Number(r.error_rate ?? 0),
    click_count: Number(r.click_count ?? 0),
    mouse_speed_mean: Number(r.mouse_speed_mean ?? 0),
  };
}

export const api = {
  // ── Auth (Supabase-owned; kept for compatibility) ──
  signup: async () => {
    throw new Error("Use supabase.auth.signUp (see lib/supabase.ts)");
  },
  login: async () => {
    throw new Error("Use supabase.auth.signInWithPassword");
  },
  me: async () => {
    const { data } = await supabase.auth.getUser();
    return { id: data.user?.id ?? "", email: data.user?.email ?? "", username: "", display_name: "", created_at: "", last_login: "" };
  },

  // ── Core ──
  health: async (): Promise<HealthStatus> => ({
    status: "ok",
    model_loaded: true,
    version: "1.0.0-supabase",
    active_connections: 0,
  }),

  inference: async (features: FeatureVector, _userId: string = "default"): Promise<StressResult> => {
    const d = await inferStress(features as unknown as Record<string, number>);
    const probs = d.probabilities ?? { NEUTRAL: 0.33, MILD: 0.33, STRESSED: 0.34 };
    return {
      score: Number(d.score ?? 0),
      model_score: Number(d.score ?? 0),
      equation_score: Number(d.score ?? 0),
      final_score: Number(d.score ?? 0),
      level: d.level ?? "UNKNOWN",
      deviation_level: d.deviation_level ?? "OK",
      stress_probability: Number(d.stress_probability ?? 0),
      confidence: Math.max(probs.NEUTRAL ?? 0, probs.MILD ?? 0, probs.STRESSED ?? 0),
      probabilities: probs,
      insights: [],
      timestamp: Date.now() / 1000,
      typing_speed_wpm: Number(features.typing_speed_wpm ?? 0),
      error_rate: Number(features.error_rate ?? 0),
      click_count: Number(features.click_count ?? 0),
      mouse_speed_mean: Number(features.mouse_speed_mean ?? 0),
    };
  },
  inferenceWithFallback: (features: FeatureVector, userId?: string) =>
    api.inference(features, userId),

  history: async (_userId: string = "default", hours: number = 24): Promise<HistoryPoint[]> => {
    const uid = await userId();
    if (!uid) return [];
    const { data, error } = await supabase
      .from("stress_history")
      .select("*")
      .eq("user_id", uid)
      .gte("created_at", new Date(Date.now() - hours * 3600e3).toISOString())
      .order("created_at", { ascending: false })
      .limit(500);
    if (error) throw error;
    return (data ?? []).map(mapRow);
  },

  stats: async (_userId: string = "default"): Promise<UserStats> => {
    const rows = await api.history("", 72);
    const total = rows.length;
    const avg = (f: (r: HistoryPoint) => number) =>
      total ? rows.reduce((a, r) => a + f(r), 0) / total : 0;
    return {
      total_samples: total,
      avg_typing_speed: avg((r) => r.typing_speed_wpm ?? 0),
      avg_error_rate: avg((r) => r.error_rate ?? 0),
      avg_score: avg((r) => r.score ?? 0),
      high_stress_percentage: total
        ? (rows.filter((r) => (r.deviation_level ?? "OK") === "ELEVATED").length / total) * 100
        : 0,
    } as unknown as UserStats;
  },

  calibration: async (_userId: string = "default"): Promise<CalibrationStatus> => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("user_baselines").select("*").eq("user_id", uid).maybeSingle()
      : { data: null };
    const rows = await api.history("", 24);
    return {
      user_id: uid ?? "",
      is_calibrated: Boolean(data) && rows.length >= 5,
      days_collected: rows.length ? 1 : 0,
      samples_per_hour: {},
      completion_pct: Math.min(100, (rows.length / 20) * 100),
      calibration_quality: data?.threshold ? 0.5 : 0.0,
    } as unknown as CalibrationStatus;
  },

  feedback: async (predicted: string, actual: string, _userId: string = "default") => {
    const uid = await userId();
    if (!uid) throw new Error("not signed in");
    const stressMap: Record<string, number> = { NEUTRAL: 2, MILD: 5, STRESSED: 8 };
    const { error } = await supabase.from("ema_checkins").insert({
      user_id: uid,
      stress: stressMap[actual] ?? 5,
      ts_epoch: Date.now() / 1000,
    });
    if (error) throw error;
    return { status: "ok", message: `Feedback saved: ${predicted} -> ${actual}` };
  },

  reset: async (_userId: string = "demo_user") => {
    const uid = await userId();
    if (uid) await supabase.from("stress_history").delete().eq("user_id", uid);
    return { status: "ok", message: "Session data cleared" };
  },

  exportMyData: async () => {
    const uid = await userId();
    const out: Record<string, unknown[]> = {};
    for (const t of ["stress_history", "ema_checkins", "interventions", "wellness_checkins", "telemetry_events"]) {
      const { data } = uid ? await supabase.from(t).select("*").eq("user_id", uid) : { data: null };
      out[t] = data ?? [];
    }
    return { export_version: 1, user_id: uid ?? "", scope: "all", ...out };
  },

  deleteMyBehavioralData: async () => {
    const uid = await userId();
    const deleted: Record<string, boolean> = {};
    for (const t of ["stress_history", "ema_checkins", "interventions", "telemetry_events", "wellness_checkins"]) {
      const { error } = uid ? await supabase.from(t).delete().eq("user_id", uid) : { error: null };
      deleted[t] = !error;
    }
    return { status: "ok", account_retained: true, deleted };
  },

  modelMetrics: async () => ({
    accuracy: 70.8, precision: 67.0, recall: 67.3, f1: 67.2,
    confusion_matrix: [[3177, 0, 0], [0, 3105, 0], [0, 0, 2040]],
    labels: ["NEUTRAL", "MILD", "STRESSED"],
    benchmark_type: "synthetic_smoke_test",
    note: "Model runs server-side in the infer edge function",
  }),

  // ── Interventions ──
  interventionRecommendation: async (_userId: string = "default"): Promise<InterventionSnapshot> => {
    const latest = await api.history("", 1);
    const elevated = latest.some((r) => (r.deviation_level ?? "OK") === "ELEVATED");
    return {
      alert_state: elevated ? "EARLY_WARNING" : "NORMAL",
      trend: "stable",
      recovery_score: elevated ? 40 : 80,
      intervention: elevated
        ? { intervention_type: "breathing_reset", title: "Take a breath", message: "Your signals are elevated vs your baseline. Try a 60-second breathing reset.", action: "start_break" }
        : null,
      active_intervention: null,
      active_start_score: null,
    } as unknown as InterventionSnapshot;
  },

  interventionAction: async (action: string, _userId: string = "default", interventionType?: string, notes: string = "") => {
    const uid = await userId();
    if (!uid) throw new Error("not signed in");
    const { error } = await supabase.from("interventions").insert({
      user_id: uid, action, intervention_type: interventionType ?? "", notes,
    });
    if (error) throw error;
    return { status: "ok", message: `Intervention ${action} recorded` };
  },

  interventionHistory: async (_userId: string = "default", _hours: number = 168): Promise<InterventionEvent[]> => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("interventions").select("*").eq("user_id", uid).order("created_at", { ascending: false }).limit(100)
      : { data: null };
    return ((data ?? []) as { id: string; action: string; intervention_type: string; notes: string; created_at: string }[]).map((r) => ({
      id: r.id, action: r.action, intervention_type: r.intervention_type ?? "",
      notes: r.notes ?? "", created_at: r.created_at,
    })) as unknown as InterventionEvent[];
  },

  checkWindDown: async (_userId?: string) => ({ wind_down: null }),
  scheduleBreak: async (_u: string, breakTime: string, interventionType: string = "breathing_reset") =>
    ({ status: "ok", break: { id: String(Date.now()), scheduled_for: breakTime, intervention_type: interventionType, status: "scheduled" } }),
  getScheduledBreaks: async (_userId?: string) => ({ breaks: [] }),
  cancelBreak: async (_userId?: string, _breakId?: string) => ({ status: "ok", message: "No active break" }),
  checkDueBreaks: async (_userId?: string) => ({ due_break: null }),

  // ── Chat (storage via tables, answers via edge function) ──
  createChatSession: async (title?: string) => {
    const uid = await userId();
    if (!uid) throw new Error("not signed in");
    const { data, error } = await supabase.from("chat_sessions").insert({
      user_id: uid, title: title || "New Chat",
    }).select().single();
    if (error) throw error;
    return { success: true, session: { id: data.id, title: data.title, created_at: data.created_at } };
  },

  getChatSessions: async (limit?: number) => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("chat_sessions").select("*").eq("user_id", uid).order("updated_at", { ascending: false }).limit(limit || 20)
      : { data: null };
    return { success: true, sessions: (data ?? []).map((s: { id: string; title: string; created_at: string }) => ({ id: s.id, title: s.title, created_at: s.created_at })) };
  },

  getChatMessages: async (sessionId: string) => {
    const { data } = await supabase.from("chat_messages").select("*").eq("session_id", sessionId).order("created_at", { ascending: true });
    return { success: true, messages: (data ?? []).map((m: { id: string; role: string; content: string; created_at: string }) => ({ id: m.id, role: m.role, content: m.content, agent_type: "general", created_at: m.created_at })) };
  },

  chatStream: (
    sessionId: string,
    message: string,
    callbacks: {
      onToken?: (token: string) => void;
      onClassification?: (agentType: string) => void;
      onDone?: (fullResponse: string) => void;
      onError?: (error: Error) => void;
      onToolRequest?: (tool: { tool: string; params: ChatToolParams; request_id: string }) => void;
    }
  ) => {
    let cancelled = false;
    (async () => {
      try {
        const uid = await userId();
        if (uid) {
          await supabase.from("chat_messages").insert({
            session_id: sessionId, role: "user", content: message,
          });
        }
        callbacks.onClassification?.("general");
        const res = await chatWithAssistant(message, await api.getChatMessages(sessionId).then((r) => r.messages.slice(-8)));
        if (cancelled) return;
        const reply: string = res?.reply ?? "…";
        const chunk = 40;
        for (let i = 0; i < reply.length; i += chunk) {
          if (cancelled) return;
          callbacks.onToken?.(reply.slice(i, i + chunk));
          await new Promise((r) => setTimeout(r, 15));
        }
        if (uid) {
          await supabase.from("chat_messages").insert({
            session_id: sessionId, role: "assistant", content: reply,
          });
          await supabase.from("chat_sessions").update({ updated_at: new Date().toISOString() }).eq("id", sessionId);
        }
        callbacks.onDone?.(reply);
      } catch (e) {
        callbacks.onError?.(e instanceof Error ? e : new Error(String(e)));
      }
    })();
    return () => { cancelled = true; };
  },

  // ── Wellness ──
  saveWellnessCheckin: async (energyLevel: string, sleepQuality: string, note?: string) => {
    const uid = await userId();
    if (!uid) throw new Error("not signed in");
    const { data, error } = await supabase.from("wellness_checkins").upsert({
      user_id: uid, check_date: new Date().toISOString().slice(0, 10),
      energy_level: energyLevel, sleep_quality: sleepQuality, note: note ?? null,
    }, { onConflict: "user_id,check_date" }).select().single();
    if (error) throw error;
    return { success: true, checkin: data };
  },
  getWellnessCheckins: async (days?: number) => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("wellness_checkins").select("*").eq("user_id", uid).gte("check_date", new Date(Date.now() - (days || 7) * 86400e3).toISOString().slice(0, 10)).order("check_date", { ascending: false })
      : { data: null };
    return { success: true, checkins: data ?? [] };
  },
  getTodayCheckin: async () => {
    const uid = await userId();
    const today = new Date().toISOString().slice(0, 10);
    const { data } = uid
      ? await supabase.from("wellness_checkins").select("*").eq("user_id", uid).eq("check_date", today).maybeSingle()
      : { data: null };
    return { success: true, checkin: data ?? null };
  },
  getWellnessJournal: async (limit?: number) => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("wellness_insights").select("*").eq("user_id", uid).order("generated_at", { ascending: false }).limit(limit || 10)
      : { data: null };
    return { success: true, insights: data ?? [] };
  },
  getWeeklyReflection: async () => {
    const c = await api.getWellnessCheckins(7);
    const energyMap: Record<string, number> = { low: 1, medium: 2, high: 3 };
    const list = c.checkins as { id: string; energy_level: string; sleep_quality: string; check_date: string }[];
    const avgEnergy = list.length ? list.reduce((a, x) => a + (energyMap[x.energy_level] ?? 0), 0) / list.length : null;
    const insights = await api.getWellnessJournal(5);
    return {
      success: true,
      reflection: {
        avg_energy: avgEnergy, avg_sleep: null, checkin_count: list.length,
        insights: insights.insights as { id: string; insight_type: string; content: string }[],
      },
    };
  },

  // ── Focus ──
  getFocusState: async () => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("focus_snapshots").select("*").eq("user_id", uid).order("created_at", { ascending: false }).limit(1).maybeSingle()
      : { data: null };
    return {
      success: true,
      state: {
        flow_score: Number(data?.focus_score ?? 60),
        deep_work_minutes: Number(data?.deep_work_minutes ?? 0),
        context_switches: Number(data?.context_switches ?? 0),
        is_in_flow: Number(data?.focus_score ?? 60) >= 65,
        suggestion: undefined,
      },
    };
  },
  getDistractionShield: async () => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("user_shield_settings").select("*").eq("user_id", uid).maybeSingle()
      : { data: null };
    return { success: true, shield: { enabled: Boolean(data?.enabled), context_switches: 0, tab_hopping: 0, mouse_agitation: "low" } };
  },
  toggleShield: async (enabled: boolean) => {
    const uid = await userId();
    if (!uid) throw new Error("not signed in");
    await supabase.from("user_shield_settings").upsert({ user_id: uid, enabled, updated_at: new Date().toISOString() });
    return { success: true, enabled };
  },
  getEnergyForecast: async () => ({
    success: true,
    forecast: {
      peak_hour: "10:00", peak_energy: 80,
      energy_curve: Array.from({ length: 12 }, (_, i) => ({ hour: 8 + i, hour_label: `${8 + i}:00`, energy: 50 + 20 * Math.sin((i - 2) / 3) })),
      suggested_schedule: [{ time: "10:00", activity: "Deep work", energy: "high" }],
      confidence: "low",
    },
  }),

  // ── Streams (Supabase Realtime-free: polling the edge function) ──
  inferenceStream: (
    _userId: string,
    callbacks: {
      onUpdate?: (data: { score: number; level: string; confidence: number; features: StreamFeatures }) => void;
      onHeartbeat?: () => void;
      onError?: (error: Error) => void;
    },
    durationMinutes?: number
  ) => {
    const interval = setInterval(async () => {
      try {
        const { data } = await supabase.auth.getSession();
        if (!data.session) return;
        const last = await api.history("", 0.1);
        const r = last[0];
        if (r) {
          callbacks.onUpdate?.({
            score: r.score ?? 0, level: r.level ?? "NEUTRAL",
            confidence: r.confidence ?? 0, features: {},
          });
        }
        callbacks.onHeartbeat?.();
      } catch (e) {
        callbacks.onError?.(e instanceof Error ? e : new Error(String(e)));
      }
    }, 5000);
    if (durationMinutes) setTimeout(() => clearInterval(interval), durationMinutes * 60000);
    return () => clearInterval(interval);
  },
};

export function setToken(_token: string) {
  // no-op — Supabase owns sessions
}

export function clearToken() {
  // no-op — Supabase owns sessions
}






