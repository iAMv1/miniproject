/** MindPulse — API Client */

import type { FeatureVector, StressResult, HistoryPoint, CalibrationStatus, UserStats, HealthStatus } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
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
};
