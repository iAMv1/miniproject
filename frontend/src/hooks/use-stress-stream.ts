/** MindPulse — WebSocket Hook */

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { StressResult } from "@/lib/types";

type ConnectionStatus = "connected" | "connecting" | "disconnected";

interface UseStressStreamReturn {
  data: StressResult | null;
  history: StressResult[];
  status: ConnectionStatus;
  send: (features: Record<string, number>, userId?: string) => void;
}

export function useStressStream(): UseStressStreamReturn {
  const [data, setData] = useState<StressResult | null>(null);
  const [history, setHistory] = useState<StressResult[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    const url = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:5000/api/v1/ws/stress";
    try {
      setStatus("connecting");
      const ws = new WebSocket(url);
      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setStatus("connected");
      };
      ws.onclose = () => {
        setStatus("disconnected");
        reconnectAttemptsRef.current += 1;
        const jitter = Math.floor(Math.random() * 800);
        const backoff = Math.min(
          10000,
          2000 + reconnectAttemptsRef.current * 500 + jitter,
        );
        reconnectTimer.current = setTimeout(connect, backoff);
      };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "ping") {
            ws.send(JSON.stringify({ type: "pong", timestamp: Date.now() }));
            return;
          }
          if (msg.type === "stress_update") {
            const result: StressResult = {
              score: msg.score,
              model_score: msg.model_score,
              equation_score: msg.equation_score,
              final_score: msg.final_score,
              level: msg.level,
              confidence: msg.confidence,
              probabilities: msg.probabilities,
              feature_contributions: msg.feature_contributions ?? {},
              insights: msg.insights || [],
              timestamp: msg.timestamp || Date.now(),
              typing_speed_wpm: msg.typing_speed_wpm ?? 0,
              rage_click_count: msg.rage_click_count ?? 0,
              error_rate: msg.error_rate ?? 0,
              click_count: msg.click_count ?? 0,
              mouse_speed_mean: msg.mouse_speed_mean ?? 0,
              mouse_reentry_count: msg.mouse_reentry_count ?? 0,
              mouse_reentry_latency_ms: msg.mouse_reentry_latency_ms ?? 0,
              alert_state: msg.alert_state ?? "NORMAL",
              intervention: msg.intervention ?? null,
              trend: msg.trend ?? "steady",
              recovery_score: msg.recovery_score ?? 0,
            };
            setData(result);
            setHistory((prev) => [...prev.slice(-120), result]);
          } else if (msg.type === "session_reset") {
            setData(null);
            setHistory([]);
          }
        } catch {}
      };
      ws.onerror = () => ws.close();
      wsRef.current = ws;
    } catch {
      setStatus("disconnected");
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((features: Record<string, number>, userId: string = "default") => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "features", features, user_id: userId }));
    }
  }, []);

  return { data, history, status, send };
}
