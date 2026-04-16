"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { HistoryPoint, UserStats, InterventionEvent } from "@/lib/types";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from "recharts";

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [interventions, setInterventions] = useState<InterventionEvent[]>([]);
  const [hours, setHours] = useState(24);

  useEffect(() => {
    api.history("default", hours).then(setHistory).catch(() => {});
    api.stats().then(setStats).catch(() => {});
    api.interventionHistory("default", Math.max(24, hours)).then(setInterventions).catch(() => {});
  }, [hours]);

  const chartData = history.map((h) => ({
    time: new Date(h.timestamp * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    score: h.score,
    level: h.level,
  }));

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">Stress History</h1>
        <p className="text-sm text-muted mt-1">Track your stress patterns over time</p>
      </div>

      {/* Time Range Selector */}
      <div className="flex gap-2">
        {[6, 12, 24, 48, 168].map((h) => (
          <button
            key={h}
            onClick={() => setHours(h)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              hours === h ? "bg-accent text-white" : "bg-surface border border-border text-muted hover:text-white"
            }`}
          >
            {h < 24 ? `${h}h` : h === 24 ? "1d" : h === 168 ? "7d" : `${h / 24}d`}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <h3 className="text-sm text-muted mb-3">Stress Timeline</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="stressGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6C5CE7" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#6C5CE7" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" tick={{ fill: "#a0a0b0", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fill: "#a0a0b0", fontSize: 11 }} axisLine={false} tickLine={false} width={30} />
            <Tooltip
              contentStyle={{ background: "#1E1E2E", border: "1px solid #3A3A4A", borderRadius: 8 }}
              labelStyle={{ color: "#a0a0b0" }}
            />
            <ReferenceLine y={40} stroke="#2ecc71" strokeDasharray="4 4" strokeOpacity={0.4} />
            <ReferenceLine y={70} stroke="#e74c3c" strokeDasharray="4 4" strokeOpacity={0.4} />
            <Area type="monotone" dataKey="score" stroke="#6C5CE7" fill="url(#stressGrad)" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs text-muted">Average Score</div>
          <div className="text-2xl font-bold mt-1">{stats?.avg_score?.toFixed(1) ?? "--"}</div>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs text-muted">Stressed %</div>
          <div className="text-2xl font-bold mt-1 text-stressed">{stats?.stressed_pct ?? 0}%</div>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4">
          <div className="text-xs text-muted">Total Samples</div>
          <div className="text-2xl font-bold mt-1">{stats?.total_samples ?? 0}</div>
        </div>
      </div>

      {/* Recent Entries */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <h3 className="text-sm text-muted mb-3">Recent Readings</h3>
        <div className="space-y-2 max-h-60 overflow-auto">
          {history.slice(-20).reverse().map((h, i) => {
            const color = h.level === "NEUTRAL" ? "text-neutral" : h.level === "MILD" ? "text-mild" : "text-stressed";
            return (
              <div key={i} className="flex items-center justify-between py-1 border-b border-border/50 last:border-0">
                <span className="text-xs text-muted">
                  {new Date(h.timestamp * 1000).toLocaleTimeString()}
                </span>
                <span className={`text-sm font-medium ${color}`}>{h.score.toFixed(1)}</span>
                <span className={`text-xs ${color}`}>{h.level}</span>
              </div>
            );
          })}
          {history.length === 0 && <p className="text-sm text-muted">No history yet. Start tracking to collect data.</p>}
        </div>
      </div>

      {/* Intervention Markers + Deltas */}
      <div className="rounded-xl border border-border bg-surface p-4">
        <h3 className="text-sm text-muted mb-3">Alert & Intervention Timeline</h3>
        <div className="space-y-2 max-h-60 overflow-auto">
          {interventions.slice(0, 25).map((event, i) => (
            <div key={i} className="flex items-center justify-between py-1 border-b border-border/50 last:border-0 text-xs">
              <span className="text-muted">{new Date(event.timestamp * 1000).toLocaleTimeString()}</span>
              <span>{event.action}</span>
              <span>{event.intervention_type}</span>
              <span>{event.score_before.toFixed(1)} → {event.score_after.toFixed(1)}</span>
              <span className={event.recovery_score > 0 ? "text-neutral" : "text-muted"}>
                {event.recovery_score > 0 ? `Recovery +${event.recovery_score.toFixed(1)}` : "--"}
              </span>
            </div>
          ))}
          {interventions.length === 0 && <p className="text-sm text-muted">No alert/intervention events yet.</p>}
        </div>
      </div>
    </div>
  );
}
