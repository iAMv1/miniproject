"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  isTrackingPaused,
  setTrackingPaused,
  TRACKING_PREFERENCE_EVENT,
} from "@/lib/tracking-consent";

export default function PrivacyPage() {
  const [actionStatus, setActionStatus] = useState<string | null>(null);
  const [trackingPaused, setTrackingPausedState] = useState(false);

  useEffect(() => {
    const syncPreference = () => setTrackingPausedState(isTrackingPaused());
    syncPreference();
    window.addEventListener(TRACKING_PREFERENCE_EVENT, syncPreference);
    return () => window.removeEventListener(TRACKING_PREFERENCE_EVENT, syncPreference);
  }, []);

  const handlePause = () => {
    const nextPaused = !trackingPaused;
    setTrackingPaused(nextPaused);
    setTrackingPausedState(nextPaused);
    setActionStatus(nextPaused ? "paused" : "resumed");
  };

  const handleExport = async () => {
    setActionStatus("export");
    try {
      const exportData = await api.exportMyData();
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mindpulse-data-${new Date().toISOString().split("T")[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setActionStatus("exported");
    } catch {
      setActionStatus("error");
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete all your data? This cannot be undone.")) return;
    setActionStatus("delete");
    try {
      await api.deleteMyBehavioralData();
      setTrackingPaused(true);
      setTrackingPausedState(true);
      setActionStatus("deleted");
    } catch {
      setActionStatus("error");
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white">Privacy and data</h1>
        <p className="text-sm text-muted mt-1.5">What MindPulse captures and what it never does</p>
      </div>

      {/* What We Capture */}
      <div className="rounded-lg border border-neutral/20 bg-neutral/[0.04] p-6">
        <h3 className="text-lg font-medium text-neutral mb-5">What we capture</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { title: "Keyboard", items: ["Key press/release timestamps", "Key category (alpha/digit/special)", "Hold time, flight time", "Backspace count (not content)"] },
            { title: "Mouse", items: ["Movement speed and direction", "Click timestamps", "Scroll velocity", "Quick click detection"] },
            { title: "Context", items: ["App switch timestamps", "Hashed app category", "Tab switch frequency", "Session duration"] },
          ].map((cat) => (
            <div key={cat.title} className="p-4 rounded-lg bg-surface border border-border/50">
              <h4 className="font-medium mb-3 text-white">{cat.title}</h4>
              <ul className="space-y-2">
                {cat.items.map((item) => (
                  <li key={item} className="text-xs text-muted flex gap-2 items-start">
                    <span className="text-neutral text-sm leading-none mt-0.5">✓</span> {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* What We Never Capture */}
      <div className="rounded-lg border border-stressed/20 bg-stressed/[0.04] p-6">
        <h3 className="text-lg font-medium text-stressed mb-5">What we never capture</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {["Actual keystrokes", "Typed content", "Screen content", "Page URLs", "File names", "Email content", "Chat messages", "Passwords"].map((item) => (
            <div key={item} className="flex items-center gap-2 text-sm text-muted">
              <span className="text-stressed text-sm">✗</span> {item}
            </div>
          ))}
        </div>
      </div>

      {/* Processing */}
      <div className="rounded-lg border border-border bg-surface p-6">
        <h3 className="text-lg font-medium mb-5 text-white">How processing works</h3>
        <div className="flex items-center gap-3 overflow-x-auto pb-2">
          {["Raw events", "Feature extraction", "Discard raw", "ML inference", "Score → Dashboard"].map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <div className="px-4 py-2.5 rounded-md bg-surface-hover text-sm whitespace-nowrap font-medium">{step}</div>
              {i < 4 && <span className="text-accent/60">→</span>}
            </div>
          ))}
        </div>
        <p className="text-xs text-muted mt-4">
          Feature extraction can run on your device. If telemetry sync is enabled, the service stores privacy-minimized event metadata; key values are transformed server-side and raw typed content is not persisted. Derived behavioral features are used for prediction.
        </p>
        <p className="text-xs text-muted mt-2">
          Intervention feedback stores only action/outcome metadata (helped, not helped, skipped) and score deltas.
        </p>
      </div>

      {/* Data Control */}
      <div className="rounded-lg border border-border bg-surface p-6">
        <h3 className="text-lg font-medium mb-5 text-white">Your data controls</h3>
        {actionStatus && (
          <div className={`mb-4 p-3 rounded-md text-sm ${
            actionStatus === "error" ? "bg-stressed/10 text-stressed" :
            actionStatus === "deleted" || actionStatus === "paused" || actionStatus === "exported" ? "bg-neutral/10 text-neutral" :
            "bg-accent/10 text-accent"
          }`}>
            {actionStatus === "pause" && "Pausing tracking..."}
            {actionStatus === "paused" && "Tracking is paused on this device. Stored data is unchanged."}
            {actionStatus === "resumed" && "Tracking resumed on this device."}
            {actionStatus === "export" && "Preparing your data..."}
            {actionStatus === "exported" && "Your locally stored service data was exported as JSON."}
            {actionStatus === "delete" && "Deleting all data..."}
            {actionStatus === "deleted" && "All data deleted."}
            {actionStatus === "error" && "Something went wrong. Try again."}
          </div>
        )}
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-border/50">
            <div>
              <div className="text-sm font-medium text-white">Pause tracking</div>
              <div className="text-xs text-muted mt-0.5">{trackingPaused ? "Collection is paused on this device" : "Temporarily stop local collection on this device"}</div>
            </div>
            <button
              onClick={handlePause}
              className="px-4 py-2 rounded-md border border-border text-sm font-medium hover:bg-surface-hover transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
            >
              {trackingPaused ? "Resume" : "Pause"}
            </button>
          </div>
          <div className="flex items-center justify-between py-3 border-b border-border/50">
            <div>
              <div className="text-sm font-medium text-white">Export my data</div>
              <div className="text-xs text-muted mt-0.5">Download locally stored service data as JSON</div>
            </div>
            <button
              onClick={handleExport}
              className="px-4 py-2 rounded-md border border-border text-sm font-medium hover:bg-surface-hover transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
            >
              Export
            </button>
          </div>
          <div className="flex items-center justify-between py-3">
            <div>
              <div className="text-sm font-medium text-white">Delete all data</div>
              <div className="text-xs text-muted mt-0.5">Permanently remove locally stored behavioral data; your account remains</div>
            </div>
            <button
              onClick={handleDelete}
              className="px-4 py-2 rounded-md border border-stressed/30 text-stressed text-sm font-medium hover:bg-stressed/10 transition-all duration-200 hover:scale-[0.98] active:scale-[0.96]"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
