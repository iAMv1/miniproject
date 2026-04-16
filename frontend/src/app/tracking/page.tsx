"use client";

import { useState, useEffect, useRef } from "react";
import { useStressStream } from "@/hooks/use-stress-stream";
import { api } from "@/lib/api";
import type { UserStats, InterventionRecommendation } from "@/lib/types";

// ─── SVG Arc Gauge (MindPulse's signature component) ───
function StressGauge({ score, level }: { score: number; level: string }) {
  const color = level === "NEUTRAL" ? "#2ecc71" : level === "MILD" ? "#f39c12" : "#e74c3c";
  const r = 110;
  const c = Math.PI * r;
  const offset = c - (score / 100) * c;

  return (
    <div className="flex flex-col items-center">
      <svg width="260" height="150" viewBox="0 0 260 150">
        <path d="M 20 130 A 110 110 0 0 1 240 130" fill="none" stroke="#3A3A4A" strokeWidth="14" strokeLinecap="round" />
        <path
          d="M 20 130 A 110 110 0 0 1 240 130"
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.5s ease" }}
        />
        <text x="130" y="110" textAnchor="middle" fill={color} fontSize="44" fontWeight={800} fontFamily="monospace">
          {Math.round(score)}
        </text>
        <text x="130" y="135" textAnchor="middle" fill="#a0a0b0" fontSize="13">
          / 100
        </text>
      </svg>
      <span className="text-lg font-bold tracking-wider mt-1" style={{ color }}>
        {level}
      </span>
    </div>
  );
}

// ─── Metric Tile ───
function Metric({ label, value, unit, warn }: { label: string; value: string | number; unit?: string; warn?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="text-xs text-muted uppercase tracking-wide mb-1">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-bold ${warn ? "text-stressed" : "text-white"}`}>{value}</span>
        {unit && <span className="text-sm text-muted">{unit}</span>}
      </div>
    </div>
  );
}

// ─── Insights Panel ───
function Insights({ insights, level }: { insights: string[]; level: string }) {
  if (!insights.length) return null;
  const borderColor = level === "STRESSED" ? "border-stressed/30" : level === "MILD" ? "border-mild/30" : "border-neutral/30";
  const bgColor = level === "STRESSED" ? "bg-stressed/5" : level === "MILD" ? "bg-mild/5" : "bg-neutral/5";
  return (
    <div className={`rounded-xl border ${borderColor} ${bgColor} p-4`}>
      <h3 className="text-sm font-semibold mb-2">Why this score?</h3>
      <ul className="space-y-1">
        {insights.map((insight, i) => (
          <li key={i} className="text-sm text-muted flex items-start gap-2">
            <span className="text-accent mt-0.5">•</span>
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
      <div className="rounded-xl border border-neutral/30 bg-neutral/5 p-4">
        <h3 className="text-neutral font-semibold mb-2">Calm & Focused</h3>
        <p className="text-sm text-muted">Continue at your current pace. Take a preventive 2-min eye break every 30-40 min.</p>
      </div>
    );
  }
  if (score < 70) {
    return (
      <div className="rounded-xl border border-mild/30 bg-mild/5 p-4">
        <h3 className="text-mild font-semibold mb-2">Mild Stress Detected</h3>
        <ul className="text-sm text-muted space-y-1">
          <li>• 2 minutes of slow breathing</li>
          <li>• Hydrate</li>
          <li>• Reset posture + neck stretch</li>
        </ul>
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-stressed/30 bg-stressed/5 p-4">
      <h3 className="text-stressed font-semibold mb-2">Elevated Stress</h3>
      <ol className="text-sm text-muted space-y-1 list-decimal list-inside">
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
  const { data, status } = useStressStream();
  const [stats, setStats] = useState<UserStats | null>(null);
  const prevLevelRef = useRef<string>("UNKNOWN");
  const notifPermissionRef = useRef<boolean>(false);
  const stressStreakRef = useRef<number>(0);
  const [alertState, setAlertState] = useState<"NORMAL" | "EARLY_WARNING" | "BREAK_RECOMMENDED" | "RECOVERY">("NORMAL");
  const [intervention, setIntervention] = useState<InterventionRecommendation | null>(null);
  const [activeIntervention, setActiveIntervention] = useState<string | null>(null);
  const [breakSeconds, setBreakSeconds] = useState<number>(0);

  // Request notification permission on mount
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

  // Refresh stats every 10 seconds
  useEffect(() => {
    const fetchStats = () => api.stats("demo_user").then(setStats).catch(() => {});
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    api.interventionRecommendation("demo_user")
      .then((res) => {
        setAlertState(res.alert_state);
        setIntervention(res.intervention);
        setActiveIntervention(res.active_intervention);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!breakSeconds) return;
    const timer = setInterval(() => setBreakSeconds((prev) => Math.max(0, prev - 1)), 1000);
    return () => clearInterval(timer);
  }, [breakSeconds]);

  // Fire browser notification when stress is detected
  useEffect(() => {
    if (!data) return;
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
        new Notification("⚠️ MindPulse — Stress Alert", {
          body: "Need a break now. Start your guided reset in MindPulse.",
          icon: "/favicon.ico",
          tag: "mindpulse-stress",
        });
      }
    }
    prevLevelRef.current = currentLevel;
  }, [data]);

  const score = data?.score ?? 0;
  const level = data?.level ?? "UNKNOWN";
  const insights = data?.insights ?? [];

  // Live raw features from WebSocket
  const liveWpm = data?.typing_speed_wpm ?? 0;
  const liveRageClicks = data?.rage_click_count ?? 0;
  const liveErrorRate = data?.error_rate ?? 0;
  const liveClicks = data?.click_count ?? 0;
  const interventionStateColor =
    alertState === "BREAK_RECOMMENDED"
      ? "border-stressed/40 bg-stressed/10"
      : alertState === "EARLY_WARNING"
      ? "border-mild/40 bg-mild/10"
      : alertState === "RECOVERY"
      ? "border-neutral/40 bg-neutral/10"
      : "border-border bg-surface";

  const formatBreakTimer = (total: number) => {
    const m = String(Math.floor(total / 60)).padStart(2, "0");
    const s = String(total % 60).padStart(2, "0");
    return `${m}:${s}`;
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Live Tracking</h1>
          <p className="text-sm text-muted mt-1">Real-time stress detection from typing & mouse behavior</p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={async () => {
              await api.reset("demo_user");
              setStats(null);
            }}
            className="px-4 py-1.5 rounded-lg border border-stressed/40 text-stressed text-xs font-medium hover:bg-stressed/10 transition"
          >
            ↻ Start Over
          </button>
          <div className="flex items-center gap-2 text-xs">
            <span className={`w-2 h-2 rounded-full ${status === "connected" ? "bg-neutral animate-pulse" : "bg-stressed"}`} />
            <span className="text-muted">{status}</span>
          </div>
        </div>
      </div>

      {/* Alert Banner */}
      <div className={`rounded-xl border p-4 ${interventionStateColor}`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold">
              {alertState === "BREAK_RECOMMENDED"
                ? "🚨 Break Needed Now"
                : alertState === "EARLY_WARNING"
                ? "⚠️ Early Stress Warning"
                : alertState === "RECOVERY"
                ? "✅ Recovery In Progress"
                : "🟢 Stable Work State"}
            </h3>
            <p className="text-xs text-muted mt-1">
              {data?.trend ? `Trend: ${data.trend}` : "Trend: steady"} · Confidence:{" "}
              {data ? `${(data.confidence * 100).toFixed(1)}%` : "--"}
              {data?.recovery_score ? ` · Recovery +${data.recovery_score.toFixed(1)}` : ""}
            </p>
          </div>
          <div className="text-xs text-muted">
            {intervention?.expected_benefit || "No intervention needed right now"}
          </div>
        </div>
      </div>

      {/* Sticky Active Intervention Panel */}
      {(alertState === "BREAK_RECOMMENDED" || activeIntervention) && intervention && (
        <div className="sticky top-4 z-10 rounded-xl border border-stressed/40 bg-surface p-4 shadow-lg">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-stressed">{intervention.title}</h3>
              <p className="text-xs text-muted mt-1">
                Duration: {intervention.duration_min} min · Severity: {intervention.severity}
              </p>
            </div>
            <div className="text-lg font-mono">{breakSeconds > 0 ? formatBreakTimer(breakSeconds) : "--:--"}</div>
          </div>
          <ul className="mt-3 space-y-1 text-sm text-muted">
            {intervention.steps.map((step, idx) => (
              <li key={idx}>• {step}</li>
            ))}
          </ul>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={async () => {
                await api.interventionAction("start_break", "demo_user", intervention.intervention_type);
                setActiveIntervention(intervention.intervention_type);
                setBreakSeconds(intervention.duration_min * 60);
              }}
              className="px-3 py-1.5 rounded-lg border border-neutral/30 text-neutral text-xs hover:bg-neutral/10"
            >
              Start break timer
            </button>
            <button
              onClick={async () => {
                await api.interventionAction("snooze", "demo_user", intervention.intervention_type);
                setActiveIntervention(null);
              }}
              className="px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-surface-hover"
            >
              Snooze 10 min
            </button>
            <button
              onClick={async () => {
                await api.interventionAction("im_okay", "demo_user", intervention.intervention_type);
                setActiveIntervention(null);
              }}
              className="px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-surface-hover"
            >
              I&apos;m okay
            </button>
            <button
              onClick={() => api.interventionAction("need_stronger_help", "demo_user", intervention.intervention_type)}
              className="px-3 py-1.5 rounded-lg border border-stressed/30 text-stressed text-xs hover:bg-stressed/10"
            >
              Need stronger help
            </button>
          </div>
          {breakSeconds === 0 && activeIntervention && (
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={async () => {
                  await api.interventionAction("helped", "demo_user", intervention.intervention_type);
                  setActiveIntervention(null);
                }}
                className="px-3 py-1.5 rounded-lg border border-neutral/30 text-neutral text-xs hover:bg-neutral/10"
              >
                This helped
              </button>
              <button
                onClick={async () => {
                  await api.interventionAction("not_helped", "demo_user", intervention.intervention_type);
                  setActiveIntervention(null);
                }}
                className="px-3 py-1.5 rounded-lg border border-stressed/30 text-stressed text-xs hover:bg-stressed/10"
              >
                Didn&apos;t help
              </button>
              <button
                onClick={async () => {
                  await api.interventionAction("skipped", "demo_user", intervention.intervention_type);
                  setActiveIntervention(null);
                }}
                className="px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-surface-hover"
              >
                Skipped
              </button>
            </div>
          )}
        </div>
      )}

      {/* Gauge + Stats Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 flex flex-col items-center justify-center rounded-xl border border-border bg-surface p-6">
          <StressGauge score={score} level={level} />
          <div className="mt-3 text-xs text-muted">
            Confidence: {data ? `${(data.confidence * 100).toFixed(1)}%` : "--"}
          </div>
          {data && (
            <div className="mt-2 text-[11px] text-muted text-center">
              Model: {data.model_score?.toFixed(1) ?? "--"} · Equation: {data.equation_score?.toFixed(1) ?? "--"}
            </div>
          )}
        </div>

        <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-4">
          <Metric label="Typing Speed" value={liveWpm > 0 ? liveWpm.toFixed(0) : (stats?.typing_speed_wpm?.toFixed(0) ?? "--")} unit="WPM" />
          <Metric label="Rage Clicks" value={liveRageClicks > 0 ? liveRageClicks : (stats?.rage_click_count ?? 0)} warn={liveRageClicks > 2} />
          <Metric label="Error Rate" value={liveErrorRate > 0 ? `${(liveErrorRate * 100).toFixed(1)}` : (stats?.error_rate ? `${(stats.error_rate * 100).toFixed(1)}` : "0")} unit="%" warn={liveErrorRate > 0.15} />
          <Metric label="Total Samples" value={stats?.total_samples ?? 0} />
          <Metric label="Stressed %" value={stats?.stressed_pct ?? 0} unit="%" warn={(stats?.stressed_pct ?? 0) > 30} />
          <Metric label="Current State" value={data?.level ?? stats?.current_level ?? "--"} />
        </div>
      </div>

      {/* Insights + Recommendation */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Insights insights={insights} level={level} />
        <div className="space-y-4">
          <Recommendation score={score} />
          {intervention && (
            <div className="rounded-xl border border-accent/30 bg-accent/5 p-4">
              <h3 className="text-sm font-semibold mb-2">AI Guidance</h3>
              <p className="text-xs text-muted mb-2">{intervention.expected_benefit}</p>
              <ul className="text-sm text-muted space-y-1">
                {intervention.rationale.map((reason, idx) => (
                  <li key={idx}>• {reason}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Explainability */}
      {data?.feature_contributions && Object.keys(data.feature_contributions).length > 0 && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <h3 className="text-sm text-muted mb-3">Equation Contributors</h3>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
            {Object.entries(data.feature_contributions).map(([key, value]) => (
              <div key={key} className="rounded-lg bg-surface-hover p-3">
                <div className="text-[11px] text-muted">{key}</div>
                <div className="text-lg font-semibold">{Number(value).toFixed(1)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feedback */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <h3 className="text-sm text-muted mb-3">Ground Truth Feedback</h3>
        <p className="text-xs text-muted mb-3">Help improve the model by confirming or correcting predictions.</p>
        <div className="flex gap-3">
          <button onClick={() => api.feedback(level, level, "demo_user")} className="flex-1 py-2 rounded-lg border border-neutral/30 text-neutral text-sm hover:bg-neutral/10 transition">
            Accurate
          </button>
          <button onClick={() => api.feedback(level, "NEUTRAL", "demo_user")} className="flex-1 py-2 rounded-lg border border-mild/30 text-mild text-sm hover:bg-mild/10 transition">
            Actually Relaxed
          </button>
          <button onClick={() => api.feedback(level, "STRESSED", "demo_user")} className="flex-1 py-2 rounded-lg border border-stressed/30 text-stressed text-sm hover:bg-stressed/10 transition">
            Actually Stressed
          </button>
        </div>
      </div>
    </div>
  );
}
