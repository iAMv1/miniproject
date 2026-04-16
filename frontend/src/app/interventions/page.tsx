"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InterventionEvent, InterventionSnapshot } from "@/lib/types";

export default function InterventionsPage() {
  const [snapshot, setSnapshot] = useState<InterventionSnapshot | null>(null);
  const [events, setEvents] = useState<InterventionEvent[]>([]);

  useEffect(() => {
    api.interventionRecommendation("demo_user").then(setSnapshot).catch(() => {});
    api.interventionHistory("demo_user", 168).then(setEvents).catch(() => {});
  }, []);

  const helpedEvents = events.filter((e) => e.action === "helped");
  const meanRecovery =
    helpedEvents.length > 0
      ? (helpedEvents.reduce((acc, e) => acc + (e.recovery_score || 0), 0) / helpedEvents.length).toFixed(1)
      : "0.0";

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">Interventions</h1>
        <p className="text-sm text-muted mt-1">AI guidance, active interventions, and what reduced stress</p>
      </div>

      <div className="rounded-xl border border-border bg-surface p-6">
        <h3 className="text-lg font-semibold mb-3">Current Coaching State</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-surface-hover">
            <div className="text-xs text-muted">Alert State</div>
            <div className="text-lg font-bold mt-1">{snapshot?.alert_state ?? "NORMAL"}</div>
          </div>
          <div className="p-4 rounded-lg bg-surface-hover">
            <div className="text-xs text-muted">Trend</div>
            <div className="text-lg font-bold mt-1">{snapshot?.trend ?? "steady"}</div>
          </div>
          <div className="p-4 rounded-lg bg-surface-hover">
            <div className="text-xs text-muted">Avg Recovery (helped)</div>
            <div className="text-lg font-bold mt-1 text-neutral">+{meanRecovery}</div>
          </div>
        </div>
      </div>

      {snapshot?.intervention && (
        <div className="rounded-xl border border-accent/30 bg-accent/5 p-6">
          <h3 className="text-lg font-semibold mb-2">Recommended Now: {snapshot.intervention.title}</h3>
          <p className="text-sm text-muted mb-3">{snapshot.intervention.expected_benefit}</p>
          <ul className="space-y-1 text-sm text-muted">
            {snapshot.intervention.steps.map((step, i) => (
              <li key={i}>• {step}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface p-6">
        <h3 className="text-lg font-semibold mb-3">Completed / Logged Interventions</h3>
        <div className="space-y-2 max-h-96 overflow-auto">
          {events.map((event, i) => (
            <div key={i} className="grid grid-cols-6 gap-2 text-xs border-b border-border/40 pb-2">
              <span className="text-muted">{new Date(event.timestamp * 1000).toLocaleString()}</span>
              <span>{event.action}</span>
              <span>{event.intervention_type}</span>
              <span>{event.alert_state}</span>
              <span>{event.score_before.toFixed(1)} → {event.score_after.toFixed(1)}</span>
              <span className="text-neutral">{event.recovery_score ? `+${event.recovery_score.toFixed(1)}` : "--"}</span>
            </div>
          ))}
          {events.length === 0 && <p className="text-sm text-muted">No interventions logged yet.</p>}
        </div>
      </div>
    </div>
  );
}
