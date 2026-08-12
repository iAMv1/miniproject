export const TRACKING_PREFERENCE_KEY = "mindpulse_tracking_paused";
export const TRACKING_PREFERENCE_EVENT = "mindpulse:tracking-preference";

export function isTrackingPaused(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(TRACKING_PREFERENCE_KEY) === "true";
}

export function setTrackingPaused(paused: boolean): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TRACKING_PREFERENCE_KEY, String(paused));
  window.dispatchEvent(
    new CustomEvent(TRACKING_PREFERENCE_EVENT, { detail: { paused } }),
  );
}
