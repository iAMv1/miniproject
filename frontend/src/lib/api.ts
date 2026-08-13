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

type CheckinRow = { id: string; energy_level: string; sleep_quality: string; check_date: string };

/** Derive honest pattern insights from real check-ins (no fabricated data). */
function deriveWellnessInsights(list: CheckinRow[]): { id: string; insight_type: string; content: string; generated_at: string }[] {
  const out: { id: string; insight_type: string; content: string; generated_at: string }[] = [];
  const energyMap: Record<string, number> = { low: 1, medium: 2, high: 3 };
  const today = new Date().toISOString().slice(0, 10);
  if (list.length === 0) {
    return [{
      id: "derive-nudge", insight_type: "milestone",
      content: "Log your first daily check-in — patterns start appearing after a few days.",
      generated_at: new Date().toISOString(),
    }];
  }
  if (list.length < 3) {
    out.push({
      id: "derive-start", insight_type: "milestone",
      content: `You've logged ${list.length} check-in${list.length === 1 ? "" : "s"} — keep it daily and patterns will emerge.`,
      generated_at: new Date().toISOString(),
    });
    return out;
  }
  const recent = list.slice(-3).map((c) => energyMap[c.energy_level] ?? 0);
  const before = list.slice(-6, -3).map((c) => energyMap[c.energy_level] ?? 0);
  const avg = (a: number[]) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
  const recentAvg = avg(recent);
  const beforeAvg = avg(before);
  if (recentAvg > beforeAvg + 0.4) {
    out.push({ id: "derive-trend-up", insight_type: "pattern", content: "Your energy has been trending upward over the last few days.", generated_at: new Date().toISOString() });
  } else if (beforeAvg > recentAvg + 0.4) {
    out.push({ id: "derive-trend-down", insight_type: "pattern", content: "Your energy has dipped recently — consider earlier nights or a lighter load.", generated_at: new Date().toISOString() });
  } else {
    out.push({ id: "derive-trend-stable", insight_type: "pattern", content: "Your energy level has been stable across recent check-ins.", generated_at: new Date().toISOString() });
  }
  const goodSleep = list.filter((c) => ["good", "great"].includes(c.sleep_quality));
  const poorSleep = list.filter((c) => ["poor", "fair"].includes(c.sleep_quality));
  if (goodSleep.length >= 2 && poorSleep.length >= 2) {
    const gAvg = avg(goodSleep.map((c) => energyMap[c.energy_level] ?? 0));
    const pAvg = avg(poorSleep.map((c) => energyMap[c.energy_level] ?? 0));
    if (gAvg > pAvg + 0.4) {
      out.push({ id: "derive-sleep", insight_type: "pattern", content: "Days after good sleep run measurably higher-energy than days after poor sleep.", generated_at: new Date().toISOString() });
    }
  }
  const lowDays = list.filter((c) => c.energy_level === "low").length;
  if (lowDays >= Math.max(2, Math.floor(list.length / 2))) {
    out.push({ id: "derive-low", insight_type: "suggestion", content: "Half or more of your recent check-ins were low-energy days — a longer recovery window may help.", generated_at: new Date().toISOString() });
  }
  if (list.length >= 7) {
    out.push({ id: "derive-streak", insight_type: "milestone", content: `7+ day check-in streak — your journal now covers a full week.`, generated_at: new Date().toISOString() });
  }
  if (out.length === 1 && list.length >= 3) {
    out.push({ id: "derive-note", insight_type: "suggestion", content: `Latest check-in (${today}): ${list[list.length - 1].energy_level} energy, ${list[list.length - 1].sleep_quality} sleep.`, generated_at: new Date().toISOString() });
  }
  return out;
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

  pruneStressHistory: async (olderThanDays = 90) => {
    const uid = await userId();
    if (!uid) return { success: true, pruned: 0 };
    const cutoff = new Date(Date.now() - olderThanDays * 86400e3).toISOString();
    const { error, count } = await supabase
      .from("stress_history")
      .delete({ count: "exact" })
      .eq("user_id", uid)
      .lt("created_at", cutoff);
    if (error) throw error;
    return { success: true, pruned: count ?? 0 };
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
    accuracy: 42.6, precision: 39.4, recall: 39.6, f1: 38.9,
    f1_neutral: 52.9, f1_mild: 42.1, f1_stressed: 21.7,
    binary_f1: 65.2, ece: 0.098,
    confusion_matrix: [[140, 81, 23], [81, 98, 43], [64, 65, 27]],
    labels: ["NEUTRAL", "MILD", "STRESSED"],
    benchmark_type: "fixed_subject_test_confound_free",
    note: "Real measured results: 3-class ≈ majority (honest), binary F1 0.65. Universal 3-class is not claimed. Source: training/data/model_report.json",
  }),

  // ── Interventions (real table rows; honest nulls when nothing exists) ──
  interventionRecommendation: async (_userId: string = "default"): Promise<InterventionSnapshot> => {
    const latest = await api.history("", 2);
    if (!latest.length) {
      return {
        alert_state: "NORMAL", trend: "steady", recovery_score: null,
        intervention: null, active_intervention: null, active_start_score: null,
      } as unknown as InterventionSnapshot;
    }
    const elevated = latest.some((r) => (r.deviation_level ?? "OK") === "ELEVATED");
    const trend = latest.length > 1
      ? (latest[0].score ?? 0) > (latest[1].score ?? 0) ? "rising" : "steady"
      : "steady";
    const latestScore = latest[0]?.score ?? 50;
    return {
      alert_state: elevated ? "EARLY_WARNING" : "NORMAL",
      trend,
      recovery_score: Math.max(0, Math.min(100, 100 - latestScore)),
      intervention: elevated
        ? { intervention_type: "breathing_reset", title: "Elevated vs your baseline", message: "Your behavioral signals are above your personal baseline. A short reset may help.", action: "start_break" }
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

  checkWindDown: async (_userId?: string) => {
    const latest = await api.history("", 1);
    const rising = latest.length >= 3 && (latest[0].score ?? 0) > (latest[2].score ?? 0);
    return { wind_down: rising ? { type: "behavioral", title: "Signals trending up", message: "Recent minutes are above your baseline.", severity: "mild", actions: [{ label: "Take a break", action: "start_break" }] } : null };
  },

  scheduleBreak: async (_u: string, breakTime: string, interventionType: string = "breathing_reset") => {
    const uid = await userId();
    if (!uid) throw new Error("not signed in");
    const { data, error } = await supabase.from("interventions").insert({
      user_id: uid, action: "schedule_break", intervention_type: interventionType,
      notes: `scheduled_for=${breakTime}`,
    }).select().single();
    if (error) throw error;
    return { status: "ok", break: { id: String(data.id), scheduled_for: breakTime, intervention_type: interventionType, status: "scheduled" } };
  },

  getScheduledBreaks: async (_userId?: string) => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("interventions").select("*").eq("user_id", uid).eq("action", "schedule_break").order("created_at", { ascending: false }).limit(20)
      : { data: null };
    const rows = (data ?? []) as { id: string; notes: string; intervention_type: string; created_at: string }[];
    return {
      breaks: rows.map((r) => ({
        id: String(r.id),
        scheduled_for: (r.notes ?? "").replace("scheduled_for=", "") || r.created_at,
        intervention_type: r.intervention_type ?? "",
        status: "scheduled",
        created_at: r.created_at,
      })),
    };
  },

  cancelBreak: async (_userId?: string, breakId?: string) => {
    if (!breakId) return { status: "ok", message: "No break id provided" };
    const uid = await userId();
    if (!uid) return { status: "ok", message: "Not signed in" };
    const { error } = await supabase.from("interventions").delete().eq("id", breakId).eq("user_id", uid);
    if (error) throw error;
    return { status: "ok", message: "Break cancelled" };
  },

  checkDueBreaks: async () => ({ due_break: null }),

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
            session_id: sessionId, user_id: uid, role: "user", content: message,
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
            session_id: sessionId, user_id: uid, role: "assistant", content: reply,
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
    const stored = (data ?? []) as { id: string; insight_type: string; content: string; generated_at: string }[];
    if (stored.length === 0) {
      // No stored insights yet — derive honest patterns from real check-ins.
      const c = await api.getWellnessCheckins(30);
      const list = (c.checkins as { id: string; energy_level: string; sleep_quality: string; check_date: string }[]).slice().reverse();
      return { success: true, insights: deriveWellnessInsights(list).slice(0, limit || 10), derived: true };
    }
    return { success: true, insights: stored, derived: false };
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
    if (!data) {
      // no snapshots yet — honest empty state, no fabricated score
      return { success: true, state: { flow_score: 0, deep_work_minutes: 0, context_switches: 0, is_in_flow: false, suggestion: undefined, has_data: false } };
    }
    return {
      success: true,
      state: {
        flow_score: Number(data.focus_score ?? 0),
        deep_work_minutes: Number(data.deep_work_minutes ?? 0),
        context_switches: Number(data.context_switches ?? 0),
        is_in_flow: Number(data.focus_score ?? 0) >= 65,
        suggestion: undefined,
        has_data: true,
      },
    };
  },
  getDistractionShield: async () => {
    const uid = await userId();
    const { data } = uid
      ? await supabase.from("user_shield_settings").select("*").eq("user_id", uid).maybeSingle()
      : { data: null };
    return { success: true, shield: { enabled: Boolean(data?.enabled), context_switches: 0, tab_hopping: 0, mouse_agitation: "unknown" } };
  },
  toggleShield: async (enabled: boolean) => {
    const uid = await userId();
    if (!uid) throw new Error("not signed in");
    await supabase.from("user_shield_settings").upsert({ user_id: uid, enabled, updated_at: new Date().toISOString() });
    return { success: true, enabled };
  },
  getEnergyForecast: async () => {
    // Derived from the user's REAL score history: hourly average score.
    const rows = await api.history("", 72);
    if (rows.length < 6) {
      return { success: true, forecast: null, message: "Not enough data yet — collect more sessions for an energy forecast." };
    }
    const byHour: Record<number, { sum: number; n: number }> = {};
    for (const r of rows) {
      const h = new Date(r.timestamp * 1000).getHours();
      byHour[h] = byHour[h] || { sum: 0, n: 0 };
      byHour[h].sum += r.score ?? 0;
      byHour[h].n += 1;
    }
    const curve = Object.entries(byHour)
      .map(([hour, v]) => {
        const energy = Math.max(0, Math.min(100, 100 - v.sum / v.n));
        return { hour: Number(hour), hour_label: `${hour}:00`, energy: Math.round(energy), samples: v.n };
      })
      .sort((a, b) => a.hour - b.hour);
    const peak = curve.reduce((a, b) => (b.energy > a.energy ? b : a), curve[0]);
    const busy = curve.filter((c) => c.energy >= 65).sort((a, b) => b.energy - a.energy);
    return {
      success: true,
      forecast: {
        peak_hour: `${peak.hour}:00`,
        peak_energy: peak.energy,
        energy_curve: curve,
        suggested_schedule: busy.slice(0, 3).map((c) => ({ time: `${c.hour}:00`, activity: "Deep work", energy: c.energy >= 75 ? "high" : "medium" })),
        confidence: rows.length >= 50 ? "medium" : "low",
        derived_from_samples: rows.length,
      },
    };
  },

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

export function setToken() {
  // no-op — Supabase owns sessions
}

export function clearToken() {
  // no-op — Supabase owns sessions
}








