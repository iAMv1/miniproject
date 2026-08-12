"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { StressResult } from "@/lib/types";
import { supabase, inferStress } from "@/lib/supabase";

type ConnectionStatus = "connected" | "connecting" | "disconnected" | "error";

interface UseStressStreamReturn {
  data: StressResult | null;
  history: StressResult[];
  status: ConnectionStatus;
  error: string | null;
  wsRef: React.MutableRefObject<WebSocket | null>;
}

const POLL_MS = 5000;

// Placeholder features when the collector hasn't delivered a real vector.
// The infer edge function zero-masks and clips per the training guards.
const DEFAULT_FEATURES: Record<string, number> = {
  hold_time_mean: 0, hold_time_std: 0, hold_time_median: 0,
  flight_time_mean: 0, flight_time_std: 0, typing_speed_wpm: 45,
  error_rate: 0.08, pause_frequency: 0, pause_duration_mean: 0,
  burst_length_mean: 0, rhythm_entropy: 0, mouse_speed_mean: 180,
  mouse_speed_std: 90, direction_change_rate: 1.5, click_count: 12,
  rage_click_count: 1, scroll_velocity_std: 10, tab_switch_freq: 2,
  switch_entropy: 0.8, session_fragmentation: 0, hour_of_day: 12,
  day_of_week: 2, session_duration_min: 30,
};

export function useStressStream(): UseStressStreamReturn {
  const [data, setData] = useState<StressResult | null>(null);
  const [history, setHistory] = useState<StressResult[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimer = useRef<NodeJS.Timeout | null>(null);
  const isMounted = useRef(false);
  const featuresRef = useRef<Record<string, number>>(DEFAULT_FEATURES);

  const pollOnce = useCallback(async () => {
    const { data: session } = await supabase.auth.getSession();
    if (!session.session) {
      setStatus("disconnected");
      return;
    }
    try {
      const d = await inferStress(featuresRef.current);
      const probs = d.probabilities ?? { NEUTRAL: 0.33, MILD: 0.33, STRESSED: 0.34 };
      const result: StressResult = {
        score: Number(d.score ?? 0),
        model_score: Number(d.score ?? 0),
        equation_score: Number(d.score ?? 0),
        final_score: Number(d.score ?? 0),
        level: d.level ?? "UNKNOWN",
        deviation_level: d.deviation_level ?? "OK",
        stress_probability: Number(d.stress_probability ?? 0),
        confidence: Math.max(probs.NEUTRAL ?? 0, probs.MILD ?? 0, probs.STRESSED ?? 0),
        probabilities: probs,
        feature_contributions: {},
        insights: [],
        timestamp: Date.now() / 1000,
        typing_speed_wpm: Number(featuresRef.current.typing_speed_wpm ?? 0),
        error_rate: Number(featuresRef.current.error_rate ?? 0),
        click_count: Number(featuresRef.current.click_count ?? 0),
        mouse_speed_mean: Number(featuresRef.current.mouse_speed_mean ?? 0),
        alert_state: (d.deviation_level ?? "OK") === "ELEVATED" ? "EARLY_WARNING" : "NORMAL",
        intervention: null,
        trend: "steady",
        recovery_score: (d.deviation_level ?? "OK") === "ELEVATED" ? 40 : 80,
      };
      if (!isMounted.current) return;
      setStatus("connected");
      setError(null);
      setData(result);
      setHistory((prev) => [...prev.slice(-120), result]);
    } catch (e) {
      if (!isMounted.current) return;
      setStatus("error");
      setError(e instanceof Error ? e.message : "Inference failed");
    }
  }, []);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    if (pollTimer.current) clearInterval(pollTimer.current);
    setStatus("connecting");
    pollOnce();
    pollTimer.current = setInterval(pollOnce, POLL_MS);
  }, [pollOnce]);

  useEffect(() => {
    isMounted.current = true;
    const timer = setTimeout(() => {
      if (isMounted.current) connect();
    }, 100);
    return () => {
      isMounted.current = false;
      if (pollTimer.current) clearInterval(pollTimer.current);
      if (timer) clearTimeout(timer);
    };
  }, [connect]);

  // Compat shim: pages may call wsRef.current.send() — accept a feature
  // payload to use for the next inference.
  wsRef.current = {
    send: (raw: string) => {
      try {
        const msg = JSON.parse(raw);
        if (msg.type === "features" && msg.features) {
          featuresRef.current = { ...DEFAULT_FEATURES, ...msg.features };
          pollOnce();
        }
      } catch {
        /* ignore non-JSON or unknown messages */
      }
    },
    close: () => undefined,
    readyState: 1,
  } as unknown as WebSocket;

  return { data, history, status, error, wsRef };
}
