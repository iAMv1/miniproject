"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Activity } from "lucide-react";
import { useStressStream } from "@/hooks/use-stress-stream";
import { useFeatureCollector } from "@/hooks/use-feature-collector";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import type { InterventionRecommendation, StressResult } from "@/lib/types";

type TrendPoint = { day: string; stress: number; energy: number; wpm: number; errors: number };
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from "recharts";

const SOFT_LEVEL: Record<string, string> = {
  STRESSED: "Low Energy",
  MILD: "Dipping",
  NEUTRAL: "Good Energy",
  UNKNOWN: "—",
};

function energyFromStress(score: number) {
  return 100 - score;
}

// ─── Mini Gauge Component ───
function MiniGauge({
  value,
  maxValue,
  label,
  unit,
  color,
  warnColor,
  warnThreshold,
}: {
  value: number | null;
  maxValue: number;
  label: string;
  unit: string;
  color: string;
  warnColor?: string;
  warnThreshold?: number;
}) {
  const fraction = value === null ? 0 : Math.max(0, Math.min(1, value / maxValue));
  const isWarn = value !== null && warnThreshold !== undefined && value > warnThreshold;
  const activeColor = isWarn && warnColor ? warnColor : color;

  const arcR = 40;
  const cx = 55;
  const cy = 50;
  const totalArc = Math.PI * arcR;
  const dashOffset = totalArc * (1 - fraction);

  return (
    <div className="flex flex-col items-center">
      <svg width="110" height="75" viewBox="0 0 110 75">
        <defs>
          <linearGradient id={`gauge-${label}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color} stopOpacity="0.6" />
            <stop offset="100%" stopColor={activeColor} />
          </linearGradient>
        </defs>
        <path
          d={`M ${cx - arcR} ${cy} A ${arcR} ${arcR} 0 0 1 ${cx + arcR} ${cy}`}
          fill="none"
          stroke="#1c1c2e"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <path
          d={`M ${cx - arcR} ${cy} A ${arcR} ${arcR} 0 0 1 ${cx + arcR} ${cy}`}
          fill="none"
          stroke={`url(#gauge-${label})`}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={totalArc}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1)" }}
        />
        <text
          x={cx}
          y={cy - 8}
          textAnchor="middle"
          fill="#F2EFE9"
          fontSize="18"
          fontWeight="700"
          fontFamily="system-ui, sans-serif"
        >
          {value === null ? "—" : unit === "WPM" ? Math.round(value) : value.toFixed(1)}
        </text>
        <text
          x={cx}
          y={cy + 6}
          textAnchor="middle"
          fill="#857F75"
          fontSize="8"
          fontFamily="system-ui, sans-serif"
        >
          / {maxValue}{unit ? ` ${unit}` : ""}
        </text>
      </svg>
      <span className="text-[10px] uppercase tracking-wider mt-1" style={{ color: "#857F75" }}>
        {label}
      </span>
    </div>
  );
}

// ─── SVG Semi-circle Gauge (Energy) ───
function EnergyGauge({ score, level, deviationLevel, stressProbability, trend, signalState }: {
  score: number;
  level: string;
  deviationLevel?: string;
  stressProbability?: number | null;
  trend?: string;
  signalState?: StressResult["signal_state"];
}) {
  const energy = energyFromStress(score);
  const softLevel = SOFT_LEVEL[level] ?? level;

  if (signalState !== "READY") {
    const isCalibrating = signalState === "CALIBRATING";
    const isSparse = signalState === "INSUFFICIENT_ACTIVITY";
    const title = isCalibrating
      ? "Learning your rhythm"
      : isSparse
        ? "No conclusion from this window"
        : "Waiting for a live window";
    const detail = isCalibrating
      ? "An early activity sample is available, but your baseline is not mature enough for a personal energy reading."
      : isSparse
        ? "Quiet or limited activity is not treated as a signal about how you feel."
        : "Interact normally for a short interval. MindPulse will only show a result when the input is meaningful.";
    return (
      <div className="flex min-h-[205px] max-w-[280px] flex-col justify-center text-center">
        <div className={`mx-auto grid h-12 w-12 place-items-center rounded-2xl border ${isCalibrating ? "border-[#8b7cf6]/30 bg-[#8b7cf6]/10 text-[#b8b1ff]" : "border-[#f0b35b]/30 bg-[#f0b35b]/10 text-[#f0b35b]"}`}>
          <Activity className="h-5 w-5" />
        </div>
        <p className="mt-5 text-base font-semibold tracking-[-0.02em] text-[#F4F6FB]">{title}</p>
        <p className="mt-2 text-xs leading-5 text-[#8E99B2]">{detail}</p>
        <span className="mt-4 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#8E99B2]">{isCalibrating ? "Early trend · not personalized" : "Current window · no estimate"}</span>
      </div>
    );
  }

  const gradientId =
    level === "NEUTRAL"
      ? "grad-good"
      : level === "MILD"
        ? "grad-dipping"
        : "grad-low";

  const arcR = 90;
  const cx = 130;
  const cy = 120;
  const totalArc = Math.PI * arcR;
  const fraction = Math.max(0, Math.min(1, energy / 100));
  const dashOffset = totalArc * (1 - fraction);

  return (
    <div className="flex flex-col items-center">
      <svg width="260" height="155" viewBox="0 0 260 160">
        <defs>
          <filter id="arc-glow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="grad-good" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#5b4fc4" />
            <stop offset="100%" stopColor="#22c55e" />
          </linearGradient>
          <linearGradient id="grad-dipping" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#5b4fc4" />
            <stop offset="100%" stopColor="#d97706" />
          </linearGradient>
          <linearGradient id="grad-low" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#5b4fc4" />
            <stop offset="100%" stopColor="#dc2626" />
          </linearGradient>
        </defs>
        <path
          d={`M ${cx - arcR} ${cy} A ${arcR} ${arcR} 0 0 1 ${cx + arcR} ${cy}`}
          fill="none"
          stroke="#1c1c2e"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d={`M ${cx - arcR} ${cy} A ${arcR} ${arcR} 0 0 1 ${cx + arcR} ${cy}`}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={totalArc}
          strokeDashoffset={dashOffset}
          filter="url(#arc-glow)"
          style={{
            transition:
              "stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.5s ease",
          }}
        />
        <text
          x={cx}
          y={cy - 18}
          textAnchor="middle"
          fill="#F2EFE9"
          fontSize="44"
          fontWeight="700"
          fontFamily="system-ui, sans-serif"
        >
          {Math.round(energy)}
        </text>
        <text
          x={cx}
          y={cy + 2}
          textAnchor="middle"
          fill="#857F75"
          fontSize="12"
          fontFamily="system-ui, sans-serif"
        >
          / 100
        </text>
      </svg>
      <span
        className="text-sm font-semibold tracking-wide mt-1"
        style={{
          color:
            level === "NEUTRAL"
              ? "#22c55e"
              : level === "MILD"
                ? "#d97706"
                : "#dc2626",
        }}
      >
        {softLevel}
      </span>
      {deviationLevel && (
        <span className="text-[10px] mt-0.5" style={{ color: "#857F75" }}>
          {deviationLevel === "ELEVATED"
            ? `Elevated vs your baseline · p=${stressProbability?.toFixed(2)}`
            : `Within your baseline · p=${stressProbability?.toFixed(2)}`}
          {trend ? ` · ${trend}` : ""}
        </span>
      )}
    </div>
  );
}

// ─── Metric Tile ───
function Metric({
  label,
  value,
  unit,
  warn,
}: {
  label: string;
  value: string | number;
  unit?: string;
  warn?: boolean;
}) {
  return (
    <div className="rounded-lg border p-4 transition-all duration-200 hover:shadow-[0_0_16px_rgba(91,79,196,0.12)]"
      style={{ background: "#141420", borderColor: "#1c1c2e" }}
    >
      <div
        className="text-[11px] uppercase tracking-wide mb-1.5 font-medium"
        style={{ color: "#857F75" }}
      >
        {label}
      </div>
      <div className="flex items-baseline gap-1">
        <span
          className="text-2xl font-semibold tabular-nums"
          style={{ color: warn ? "#dc2626" : "#F2EFE9" }}
        >
          {value}
        </span>
        {unit && <span style={{ color: "#857F75" }} className="text-sm">{unit}</span>}
      </div>
    </div>
  );
}

// ─── Insights Panel ───
function Insights({ insights, level }: { insights: string[]; level: string }) {
  if (!insights.length) return null;
  const borderColor =
    level === "STRESSED"
      ? "#dc262640"
      : level === "MILD"
        ? "#d9770640"
        : "#22c55e40";
  const bgColor =
    level === "STRESSED"
      ? "#dc262608"
      : level === "MILD"
        ? "#d9770608"
        : "#22c55e08";
  return (
    <div
      className="rounded-lg border p-4"
      style={{ borderColor, background: bgColor }}
    >
      <h3 className="text-sm font-medium mb-2" style={{ color: "#F2EFE9" }}>
        What shaped this score
      </h3>
      <ul className="space-y-1.5">
        {insights.map((insight, i) => (
          <li key={i} className="text-sm flex items-start gap-2" style={{ color: "#857F75" }}>
            <span style={{ color: "#5b4fc4" }} className="mt-0.5 text-xs">•</span>
            {insight}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── Recommendation ───
function Recommendation({ score }: { score: number }) {
  if (score < 40) {
    return (
      <div
        className="rounded-lg border p-4"
        style={{ borderColor: "#22c55e40", background: "#22c55e08" }}
      >
        <h3 className="font-medium mb-2" style={{ color: "#22c55e" }}>
          Good energy — keep going
        </h3>
        <p className="text-sm" style={{ color: "#857F75" }}>
          Continue at your current pace. Take a preventive 2-min eye break every
          30-40 min.
        </p>
      </div>
    );
  }
  if (score < 70) {
    return (
      <div
        className="rounded-lg border p-4"
        style={{ borderColor: "#d9770640", background: "#d9770608" }}
      >
        <h3 className="font-medium mb-2" style={{ color: "#d97706" }}>
          Your rhythm suggests a pause
        </h3>
        <ul className="text-sm space-y-1" style={{ color: "#857F75" }}>
          <li>• 2 minutes of slow breathing</li>
          <li>• Hydrate</li>
          <li>• Reset posture and neck stretch</li>
        </ul>
      </div>
    );
  }
  return (
    <div
      className="rounded-lg border p-4"
      style={{ borderColor: "#dc262640", background: "#dc262608" }}
    >
      <h3 className="font-medium mb-2" style={{ color: "#dc2626" }}>
        Consider a reset
      </h3>
      <ol className="text-sm space-y-1 list-decimal list-inside" style={{ color: "#857F75" }}>
        <li>4 cycles of box breathing</li>
        <li>5-minute screen break</li>
        <li>Resume with one priority task only</li>
      </ol>
    </div>
  );
}

// ─── Main Page ───
export default function TrackingPage() {
  const MIN_STRESS_STREAK_FOR_ALERT = 2;
  const CRITICAL_STRESS_SCORE = 85;
  const MIN_CONFIDENCE_FOR_CRITICAL_ALERT = 0.7;
  const { userId } = useAuth();
  const { data: wsData, history: wsHistory, status, error: wsError, wsRef } = useStressStream();

  const wsSend = useCallback(
    (data: string) => {
      if (wsRef?.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data);
      }
    },
    [wsRef],
  );

  useFeatureCollector(wsSend, userId, 30000);
  const [trendData, setTrendData] = useState<TrendPoint[]>([]);
  const prevLevelRef = useRef<string>("UNKNOWN");
  const notifPermissionRef = useRef<boolean>(false);
  const stressStreakRef = useRef<number>(0);
  const [alertState, setAlertState] = useState<
    "NORMAL" | "EARLY_WARNING" | "BREAK_RECOMMENDED" | "RECOVERY"
  >("NORMAL");
  const [intervention, setIntervention] =
    useState<InterventionRecommendation | null>(null);
  const [activeIntervention, setActiveIntervention] = useState<string | null>(
    null,
  );
  const [breakSeconds, setBreakSeconds] = useState<number>(0);
  const [windDown, setWindDown] = useState<{
    type: string;
    title: string;
    message: string;
    severity: string;
    actions: { label: string; action: string }[];
  } | null>(null);
  const [windDownDismissed, setWindDownDismissed] = useState(false);

  // A current dashboard reading is intentionally WebSocket-only. Historical
  // sessions are not silently presented as a live state.
  const data = wsData;
  const signalState = data?.signal_state;
  const hasCurrentWindow = Boolean(data && signalState);
  const isReady = signalState === "READY";
  const readyHistory = wsHistory.filter((point) => point.signal_state === "READY");

  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      if (Notification.permission === "granted") {
        notifPermissionRef.current = true;
      } else if (Notification.permission !== "denied") {
        Notification.requestPermission().then((perm) => {
          notifPermissionRef.current = perm === "granted";
        });
      }
    }
  }, []);

  // Load 21-day trend data
  useEffect(() => {
    const fetchTrend = async () => {
      try {
        const history = await api.history(userId, 504); // 21 days * 24 hours
        if (history.length > 0) {
          // Aggregate into daily averages
          const dailyMap = new Map<string, { score: number; count: number; wpm: number; errors: number; energy: number }>();
          history.forEach((h) => {
            const day = new Date(h.timestamp).toLocaleDateString([], { month: "short", day: "numeric" });
            const existing = dailyMap.get(day) || { score: 0, count: 0, wpm: 0, errors: 0, energy: 0 };
            dailyMap.set(day, {
              score: existing.score + h.score,
              count: existing.count + 1,
              wpm: existing.wpm + (h.typing_speed_wpm || 0),
              errors: existing.errors + (h.error_rate || 0),
              energy: existing.energy + (100 - h.score),
            });
          });
          const trend = Array.from(dailyMap.entries())
            .slice(-21)
            .map(([day, vals]) => ({
              day,
              stress: Math.round(vals.score / vals.count),
              energy: Math.round(vals.energy / vals.count),
              wpm: Math.round(vals.wpm / vals.count),
              errors: parseFloat((vals.errors / vals.count * 100).toFixed(1)),
            }));
          setTrendData(trend);
        }
      } catch {}
    };
    fetchTrend();
  }, [userId]);

  useEffect(() => {
    api
      .interventionRecommendation(userId)
      .then((res) => {
        setAlertState(res.alert_state);
        setIntervention(res.intervention);
        setActiveIntervention(res.active_intervention);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!breakSeconds) return;
    const timer = setInterval(
      () => setBreakSeconds((prev) => Math.max(0, prev - 1)),
      1000,
    );
    return () => clearInterval(timer);
  }, [breakSeconds]);

  useEffect(() => {
    if (!data || data.signal_state !== "READY") return;
    if (data.alert_state) setAlertState(data.alert_state);
    if (data.intervention) setIntervention(data.intervention);

    const currentLevel = data.level;
    if (currentLevel === "STRESSED" && (data.confidence ?? 0) >= 0.7) {
      stressStreakRef.current += 1;
    } else {
      stressStreakRef.current = 0;
    }
    const shouldAlert =
      (data.alert_state === "BREAK_RECOMMENDED" &&
        stressStreakRef.current >= MIN_STRESS_STREAK_FOR_ALERT) ||
      (data.score >= CRITICAL_STRESS_SCORE &&
        data.confidence >= MIN_CONFIDENCE_FOR_CRITICAL_ALERT);
    if (shouldAlert && prevLevelRef.current !== "STRESSED") {
      if (notifPermissionRef.current) {
        new Notification("MindPulse — Energy dip", {
          body: "A break might help. Start your guided reset in MindPulse.",
          icon: "/favicon.ico",
          tag: "mindpulse-stress",
        });
      }
    }
    prevLevelRef.current = currentLevel;
  }, [data]);

  useEffect(() => {
    const checkWindDown = () => {
      if (windDownDismissed) return;
      api
        .checkWindDown(userId)
        .then((res) => {
          if (res.wind_down) {
            setWindDown(res.wind_down);
          }
        })
        .catch(() => {});
    };
    checkWindDown();
    const interval = setInterval(checkWindDown, 300000);
    return () => clearInterval(interval);
  }, [userId, windDownDismissed]);

  const score = isReady ? data?.score ?? 0 : 0;
  const level = isReady ? data?.level ?? "UNKNOWN" : "UNKNOWN";
  const insights = isReady ? data?.insights ?? [] : [];

  // Current-window metrics are never backfilled from long-term stats.
  const currentWpm = data?.typing_speed_wpm ?? 0;
  const currentRageClicks = data?.rage_click_count ?? 0;
  const currentErrorRate = data?.error_rate ?? 0;
  const currentMouseSpeed = data?.mouse_speed_mean ?? 0;
  // During calibration, a zero can mean that a category was not observed at
  // all. Keep it unavailable instead of presenting it as an interpreted metric.
  const liveWpm = hasCurrentWindow && (isReady || currentWpm > 0) ? currentWpm : null;
  const liveRageClicks = hasCurrentWindow && (isReady || currentRageClicks > 0) ? currentRageClicks : null;
  const liveErrorRate = hasCurrentWindow && (isReady || currentErrorRate > 0) ? currentErrorRate * 100 : null;
  const liveMouseSpeed = hasCurrentWindow && (isReady || currentMouseSpeed > 0) ? currentMouseSpeed : null;

  const formatBreakTimer = (total: number) => {
    const m = String(Math.floor(total / 60)).padStart(2, "0");
    const s = String(total % 60).padStart(2, "0");
    return `${m}:${s}`;
  };

  const alertBannerStyles: Record<string, { border: string; bg: string }> = {
    NORMAL: { border: "#1c1c2e", bg: "#141420" },
    EARLY_WARNING: { border: "rgba(217,119,6,0.3)", bg: "rgba(217,119,6,0.05)" },
    BREAK_RECOMMENDED: { border: "rgba(220,38,38,0.3)", bg: "rgba(220,38,38,0.05)" },
    RECOVERY: { border: "rgba(34,197,94,0.3)", bg: "rgba(34,197,94,0.05)" },
  };

  const effectiveAlertState = isReady ? alertState : "NORMAL";
  const bannerStyle = alertBannerStyles[effectiveAlertState] ?? alertBannerStyles.NORMAL;

  const statusTitle = !hasCurrentWindow
    ? "Waiting for a live activity window"
    : signalState === "INSUFFICIENT_ACTIVITY"
      ? "This window is too quiet to interpret"
      : signalState === "CALIBRATING"
        ? "Early signal — personalization is still learning"
        : effectiveAlertState === "BREAK_RECOMMENDED"
          ? "A break might help"
          : effectiveAlertState === "EARLY_WARNING"
            ? "A shift in your rhythm is emerging"
            : effectiveAlertState === "RECOVERY"
              ? "Your recent pattern is recovering"
              : "Current window is within your baseline";

  const statusDetail = !hasCurrentWindow
    ? "Move, type, or work normally for a short interval. No current conclusion is being shown."
    : signalState === "INSUFFICIENT_ACTIVITY"
      ? "A quiet window is not interpreted as calm, focused, or low strain."
      : signalState === "CALIBRATING"
        ? "The data is visible, but your personal baseline is not mature enough for a settled reading."
        : `Current personalized signal · confidence ${((data?.confidence ?? 0) * 100).toFixed(0)}%${data?.trend ? ` · ${data.trend}` : ""}`;

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto" style={{ background: "#0a0a0f" }}>
      <div className="flex items-center justify-between">
        <div>
          <h1
            className="text-3xl font-semibold tracking-tight"
            style={{ color: "#F2EFE9" }}
          >
            Your Rhythm
          </h1>
          <p className="text-sm mt-1.5" style={{ color: "#857F75" }}>
            Live behavioral signals
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={async () => {
              await api.reset(userId);
            }}
            className="px-4 py-2 rounded-lg border text-xs font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
            style={{
              borderColor: "#dc26264d",
              color: "#dc2626",
            }}
          >
            Recalibrate my baseline
          </button>
          <div className="flex items-center gap-2 text-xs">
            <span
              className="w-2 h-2 rounded-full inline-block"
              style={{
                background:
                  status === "connected"
                    ? "#22c55e"
                    : status === "error"
                      ? "#dc2626"
                      : "#d97706",
                animation:
                  status === "connected" ? "pulse 2s cubic-bezier(0.4,0,0.6,1) infinite" : undefined,
              }}
            />
            <span style={{ color: status === "error" ? "#dc2626" : "#857F75" }}>
              {status}
              {wsError ? `: ${wsError}` : ""}
            </span>
          </div>
        </div>
      </div>

      {/* Alert Banner */}
      <div
        className="rounded-lg border p-5 transition-all duration-300"
        style={{ borderColor: bannerStyle.border, background: bannerStyle.bg }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium" style={{ color: "#F2EFE9" }}>
              {statusTitle}
            </h3>
            <p className="text-xs mt-1" style={{ color: "#857F75" }}>
              {statusDetail}
            </p>
          </div>
          <div className="text-xs" style={{ color: "#857F75" }}>
            {isReady ? intervention?.expected_benefit || "No action suggested from this window" : "MindPulse is qualifying the input before offering guidance"}
          </div>
        </div>
      </div>


      {/* Wind-Down Banner */}
      {windDown && !windDownDismissed && (
        <div
          className="rounded-lg border p-5 transition-all duration-300"
          style={{
            borderColor: "#5b4fc440",
            background: "linear-gradient(135deg, #141420 0%, #1a1a2e 100%)",
            boxShadow: "0 0 24px rgba(91,79,196,0.08)",
          }}
        >
          <div className="flex items-start gap-3">
            <div className="text-2xl">🌙</div>
            <div className="flex-1">
              <h3 className="text-sm font-medium" style={{ color: "#F2EFE9" }}>
                {windDown.title}
              </h3>
              <p className="text-xs mt-1" style={{ color: "#857F75" }}>
                {windDown.message}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {windDown.actions.map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setWindDownDismissed(true);
                      setWindDown(null);
                    }}
                    className="px-3 py-1.5 rounded-lg border text-xs font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
                    style={{
                      borderColor: idx === 0 ? "#5b4fc44d" : "#1c1c2e",
                      color: idx === 0 ? "#5b4fc4" : "#857F75",
                    }}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sticky Active Intervention Panel */}
      {isReady && (alertState === "BREAK_RECOMMENDED" || activeIntervention) &&
        intervention && (
          <div
            className="sticky top-4 z-10 rounded-lg border p-5"
            style={{
              background: "#141420",
              borderColor: "#dc26264d",
              boxShadow: "0 0 24px rgba(220,38,38,0.08)",
            }}
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3
                  className="text-base font-medium"
                  style={{ color: "#dc2626" }}
                >
                  {intervention.title}
                </h3>
                <p className="text-xs mt-1" style={{ color: "#857F75" }}>
                  Duration: {intervention.duration_min} min · Severity:{" "}
                  {intervention.severity}
                </p>
              </div>
              <div
                className="text-lg font-mono tabular-nums"
                style={{ color: "#F2EFE9" }}
              >
                {breakSeconds > 0 ? formatBreakTimer(breakSeconds) : "--:--"}
              </div>
            </div>
            <ul className="mt-3 space-y-1.5 text-sm" style={{ color: "#857F75" }}>
              {intervention.steps.map((step, idx) => (
                <li key={idx}>• {step}</li>
              ))}
            </ul>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={async () => {
                  await api.interventionAction(
                    "start_break",
                    userId,
                    intervention.intervention_type,
                  );
                  setActiveIntervention(intervention.intervention_type);
                  setBreakSeconds(intervention.duration_min * 60);
                }}
                className="px-4 py-2 rounded-lg border text-xs font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
                style={{ borderColor: "#22c55e4d", color: "#22c55e" }}
              >
                Start my break
              </button>
              <button
                onClick={async () => {
                  await api.interventionAction(
                    "snooze",
                    userId,
                    intervention.intervention_type,
                  );
                  setActiveIntervention(null);
                }}
                className="px-4 py-2 rounded-lg border text-xs font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
                style={{ borderColor: "#1c1c2e", color: "#857F75" }}
              >
                Remind me later
              </button>
              <button
                onClick={async () => {
                  await api.interventionAction(
                    "im_okay",
                    userId,
                    intervention.intervention_type,
                  );
                  setActiveIntervention(null);
                }}
                className="px-4 py-2 rounded-lg border text-xs font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
                style={{ borderColor: "#1c1c2e", color: "#857F75" }}
              >
                I&apos;m okay, thanks
              </button>
            </div>
          </div>
        )}

      {/* ─── Main Gauge + Mini Gauges ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Energy Gauge */}
        <div
          className="lg:col-span-1 flex flex-col items-center justify-center rounded-lg border p-6"
          style={{ background: "#141420", borderColor: "#1c1c2e" }}
        >
          <EnergyGauge score={score} level={level}
            deviationLevel={data?.deviation_level}
            stressProbability={data?.stress_probability}
            trend={data?.trend}
            signalState={signalState} />
        </div>

        {/* Mini Gauges: WPM, Error Rate, Clicks, Mouse Speed */}
        <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-lg border p-4 flex flex-col items-center justify-center"
            style={{ background: "#141420", borderColor: "#1c1c2e" }}>
            <MiniGauge
              value={liveWpm}
              maxValue={120}
              label="Typing Speed"
              unit="WPM"
              color="#5b4fc4"
            />
          </div>
          <div className="rounded-lg border p-4 flex flex-col items-center justify-center"
            style={{ background: "#141420", borderColor: "#1c1c2e" }}>
            <MiniGauge
              value={liveErrorRate}
              maxValue={30}
              label="Error Rate"
              unit="%"
              color="#22c55e"
              warnColor="#dc2626"
              warnThreshold={15}
            />
          </div>
          <div className="rounded-lg border p-4 flex flex-col items-center justify-center"
            style={{ background: "#141420", borderColor: "#1c1c2e" }}>
            <MiniGauge
              value={liveRageClicks}
              maxValue={10}
              label="Rage Clicks"
              unit=""
              color="#d97706"
              warnColor="#dc2626"
              warnThreshold={3}
            />
          </div>
          <div className="rounded-lg border p-4 flex flex-col items-center justify-center"
            style={{ background: "#141420", borderColor: "#1c1c2e" }}>
            <MiniGauge
              value={liveMouseSpeed}
              maxValue={500}
              label="Mouse Speed"
              unit="px/s"
              color="#3b82f6"
            />
          </div>
        </div>
      </div>

      {/* ─── 21-Day Trend Chart ─── */}
      {trendData.length > 1 && (
        <div
          className="rounded-lg border p-5"
          style={{ background: "#141420", borderColor: "#1c1c2e" }}
        >
          <h3 className="text-sm mb-4 font-medium" style={{ color: "#F2EFE9" }}>
            21-Day Trends
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c1c2e" />
              <XAxis dataKey="day" stroke="#857F75" fontSize={10} tick={{ fill: "#857F75" }} />
              <YAxis stroke="#857F75" fontSize={10} tick={{ fill: "#857F75" }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{
                  background: "#141420",
                  border: "1px solid #1c1c2e",
                  borderRadius: "8px",
                  color: "#F2EFE9",
                  fontSize: "12px",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px" }} />
              <Line type="monotone" dataKey="energy" stroke="#22c55e" strokeWidth={2} dot={false} name="Energy" />
              <Line type="monotone" dataKey="stress" stroke="#dc2626" strokeWidth={2} dot={false} name="Stress" />
              <Line type="monotone" dataKey="wpm" stroke="#5b4fc4" strokeWidth={2} dot={false} name="WPM" yAxisId="right" />
              <YAxis yAxisId="right" orientation="right" stroke="#5b4fc4" fontSize={10} tick={{ fill: "#5b4fc4" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ─── Energy Trend Sparkline (last 30 min) ─── */}
      <div
        className="rounded-lg border p-5"
        style={{ background: "#141420", borderColor: "#1c1c2e" }}
      >
        <h3 className="text-sm mb-4 font-medium" style={{ color: "#857F75" }}>
          Your energy trend (last 30 min)
        </h3>
        {readyHistory.length > 1 ? (
          <div className="h-24">
            <svg width="100%" height="100%" viewBox="0 0 600 100" preserveAspectRatio="none">
              <defs>
                <linearGradient id="energy-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#5b4fc4" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="#5b4fc4" stopOpacity="0" />
                </linearGradient>
              </defs>
              {(() => {
                const points = readyHistory.slice(-30).map((h, i, arr) => {
                  const x = (i / (arr.length - 1)) * 600;
                  const y = 100 - (energyFromStress(h.score) / 100) * 100;
                  return { x, y };
                });
                const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
                const areaPath = `${linePath} L 600 100 L 0 100 Z`;
                return (
                  <>
                    <path d={areaPath} fill="url(#energy-gradient)" />
                    <path d={linePath} fill="none" stroke="#5b4fc4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    {points.length > 0 && (
                      <circle cx={points[points.length - 1].x} cy={points[points.length - 1].y} r="4" fill="#5b4fc4" />
                    )}
                  </>
                );
              })()}
            </svg>
          </div>
        ) : isReady ? (
          <div className="h-24 flex items-center justify-center">
            <span className="text-xs" style={{ color: "#857F75" }}>
              Building trend line...
            </span>
          </div>
        ) : (
          <div className="h-24 flex items-center justify-center">
            <span className="text-xs" style={{ color: "#857F75" }}>
              Collecting data...
            </span>
          </div>
        )}
      </div>

      {/* ─── Insights + Recommendation ─── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Insights insights={insights} level={level} />
          <div className="space-y-4">
            {isReady ? (
              <Recommendation score={score} />
            ) : (
              <div className="rounded-lg border p-4" style={{ borderColor: "#1c1c2e", background: "#141420" }}>
                <h3 className="font-medium mb-2" style={{ color: "#F2EFE9" }}>No guidance from an incomplete signal</h3>
                <p className="text-sm" style={{ color: "#857F75" }}>MindPulse will wait for a ready personal window before suggesting a break, focus mode, or next step.</p>
              </div>
            )}
            {isReady && intervention && (
            <div
              className="rounded-lg border p-4"
              style={{ borderColor: "#5b4fc433", background: "#5b4fc408" }}
            >
              <h3 className="text-sm font-medium mb-2" style={{ color: "#F2EFE9" }}>
                AI guidance
              </h3>
              <p className="text-xs mb-2" style={{ color: "#857F75" }}>
                {intervention.expected_benefit}
              </p>
              <ul className="text-sm space-y-1" style={{ color: "#857F75" }}>
                {intervention.rationale.map((reason, idx) => (
                  <li key={idx}>• {reason}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* ─── Feedback ─── */}
      <div
        className="rounded-lg border p-5"
        style={{ background: "#141420", borderColor: "#1c1c2e" }}
      >
        <h3 className="text-sm mb-3 font-medium" style={{ color: "#857F75" }}>
          Help me learn you better
        </h3>
          <p className="text-xs mb-4" style={{ color: "#857F75" }}>
            {isReady
              ? "Your context can confirm or correct this personalized window."
              : "Feedback unlocks after a ready personal signal, so you are never asked to validate a guess."}
          </p>
          {isReady ? (
            <div className="flex gap-3">
              <button
                onClick={() => api.feedback(level, level, userId)}
                className="flex-1 py-2.5 rounded-lg border text-sm font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
                style={{ borderColor: "#22c55e4d", color: "#22c55e" }}
              >
                This fits
              </button>
              <button
                onClick={() => api.feedback(level, "NEUTRAL", userId)}
                className="flex-1 py-2.5 rounded-lg border text-sm font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
                style={{ borderColor: "#d977064d", color: "#d97706" }}
              >
                I feel more settled
              </button>
              <button
                onClick={() => api.feedback(level, "STRESSED", userId)}
                className="flex-1 py-2.5 rounded-lg border text-sm font-medium transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
                style={{ borderColor: "#dc26264d", color: "#dc2626" }}
              >
                I feel more strained
              </button>
            </div>
          ) : (
            <div className="rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3 text-xs leading-5 text-[#8E99B2]">
              Keep working normally for a short interval. The dashboard will show a distinct early-signal or ready state rather than manufacturing a live score.
            </div>
          )}
      </div>
    </div>
  );
}
