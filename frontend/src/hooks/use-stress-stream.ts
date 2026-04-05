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

  const connect = useCallback(() => {
    const url = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:5000/api/v1/ws/stress";
    try {
      setStatus("connecting");
      const ws = new WebSocket(url);
      ws.onopen = () => setStatus("connected");
      ws.onclose = () => {
        setStatus("disconnected");
        reconnectTimer.current = setTimeout(connect, 3000);
      };
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "stress_update") {
            const result: StressResult = {
              score: msg.score,
              level: msg.level,
              confidence: msg.confidence,
              probabilities: msg.probabilities,
              insights: msg.insights || [],
              timestamp: msg.timestamp || Date.now(),
              typing_speed_wpm: msg.typing_speed_wpm ?? 0,
              rage_click_count: msg.rage_click_count ?? 0,
              error_rate: msg.error_rate ?? 0,
              click_count: msg.click_count ?? 0,
              mouse_speed_mean: msg.mouse_speed_mean ?? 0,
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
