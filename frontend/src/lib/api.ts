/** MindPulse — API Client */

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

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("mp_token");
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Auth
  signup: (email: string, username: string, password: string, displayName?: string) =>
    request<{ user: { id: number; email: string; username: string; display_name: string }; access_token: string; token_type: string }>(
      "/auth/signup",
      { method: "POST", body: JSON.stringify({ email, username, password, display_name: displayName || username }) }
    ),
  login: (emailOrUsername: string, password: string) =>
    request<{ user: { id: number; email: string; username: string; display_name: string }; access_token: string; token_type: string }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email_or_username: emailOrUsername, password }) }
    ),
  me: () => request<{ id: number; email: string; username: string; display_name: string; created_at: string; last_login: string }>("/auth/me"),

  // Core
  health: () => request<HealthStatus>("/health"),
  inference: (features: FeatureVector, userId: string = "default") =>
    request<StressResult>("/inference", {
      method: "POST",
      body: JSON.stringify({ features, user_id: userId }),
    }),
  history: (userId: string = "default", hours: number = 24) =>
    request<HistoryPoint[]>(`/history?user_id=${userId}&hours=${hours}`),
  stats: (userId: string = "default") =>
    request<UserStats>(`/stats?user_id=${userId}`),
  calibration: (userId: string = "default") =>
    request<CalibrationStatus>(`/calibration/${userId}`),
  feedback: (predicted: string, actual: string, userId: string = "default") =>
    request("/feedback", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, predicted_level: predicted, actual_level: actual, timestamp: Date.now() }),
    }),
  reset: (userId: string = "demo_user") =>
    request("/reset", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  modelMetrics: () =>
    request<{
      accuracy: number;
      precision: number;
      recall: number;
      f1: number;
      confusion_matrix: number[][];
      labels: string[];
    }>("/model-metrics"),
  interventionRecommendation: (userId: string = "default") =>
    request<InterventionSnapshot>(`/interventions/recommendation?user_id=${userId}`),
  interventionAction: (
    action: "start_break" | "snooze" | "im_okay" | "need_stronger_help" | "helped" | "not_helped" | "skipped",
    userId: string = "default",
    interventionType?: string,
    notes: string = "",
  ) =>
    request("/interventions/action", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        action,
        intervention_type: interventionType,
        notes,
      }),
    }),
  interventionHistory: (userId: string = "default", hours: number = 168) =>
    request<InterventionEvent[]>(`/interventions/history?user_id=${userId}&hours=${hours}`),
  checkWindDown: (userId: string = "default") =>
    request<{ wind_down: { type: string; title: string; message: string; severity: string; actions: { label: string; action: string }[] } | null }>(
      `/interventions/wind-down?user_id=${userId}`
    ),
  scheduleBreak: (userId: string = "default", breakTime: string, interventionType: string = "breathing_reset") =>
    request<{ status: string; break: { id: string; scheduled_for: string; intervention_type: string; status: string } }>(
      `/interventions/schedule-break?user_id=${userId}&break_time=${encodeURIComponent(breakTime)}&intervention_type=${interventionType}`,
      { method: "POST" }
    ),
  getScheduledBreaks: (userId: string = "default") =>
    request<{ breaks: { id: string; scheduled_for: string; intervention_type: string; status: string; created_at: string }[] }>(
      `/interventions/scheduled-breaks?user_id=${userId}`
    ),
  cancelBreak: (userId: string = "default", breakId: string) =>
    request<{ status: string; message: string }>(
      `/interventions/cancel-break?user_id=${userId}&break_id=${breakId}`,
      { method: "POST" }
    ),
  checkDueBreaks: (userId: string = "default") =>
    request<{ due_break: { type: string; title: string; message: string; break_id: string; intervention_type: string } | null }>(
      `/interventions/check-due-breaks?user_id=${userId}`
    ),
};

export function setToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("mp_token", token);
  }
}

export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("mp_token");
  }
}
