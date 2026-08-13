"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  isTrackingPaused,
  TRACKING_PREFERENCE_EVENT,
} from "@/lib/tracking-consent";
import { createAccumulator, computeFeatures } from "@/lib/features";
import type { FeatureAccumulator } from "@/lib/features";

export function useFeatureCollector(
  wsSend: ((data: string) => void) | null,
  userId: string,
  windowMs: number = 30000,
) {
  const accRef = useRef<FeatureAccumulator>(createAccumulator());
  const keyDownTimeRef = useRef<Map<string, number>>(new Map());
  const lastMouseRef = useRef<{ x: number; y: number; t: number } | null>(null);
  const mouseMoveThrottleRef = useRef(0);
  const isMountedRef = useRef(false);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const syncPreference = () => setPaused(isTrackingPaused());
    syncPreference();
    window.addEventListener(TRACKING_PREFERENCE_EVENT, syncPreference);
    return () => window.removeEventListener(TRACKING_PREFERENCE_EVENT, syncPreference);
  }, []);

  const flush = useCallback(() => {
    if (paused) return;
    const acc = accRef.current;
    // A window needs real measured behavior: input activity OR a measured
    // tab switch / away-gap. Pure silence is never presented as a signal.
    if (
      acc.keyPressCount === 0 &&
      acc.clickTimestamps.length === 0 &&
      acc.mouseSpeeds.length === 0 &&
      acc.tabSwitches === 0
    ) return;

    const features = computeFeatures(acc);
    if (wsSend) {
      wsSend(JSON.stringify({
        type: "features",
        features,
        tab_switch_count: acc.tabSwitches,
        user_id: userId,
      }));
    }
    accRef.current = createAccumulator();
  }, [paused, wsSend, userId]);

  useEffect(() => {
    if (paused) {
      accRef.current = createAccumulator();
      return;
    }
    isMountedRef.current = true;
    const flushTimer = setInterval(flush, windowMs);

    const markHidden = () => {
      const acc = accRef.current;
      if (acc.hiddenStart === null) {
        acc.hiddenStart = performance.now();
        acc.tabSwitches++;
      }
    };
    const markVisible = () => {
      const acc = accRef.current;
      if (acc.hiddenStart !== null) {
        const gap = (performance.now() - acc.hiddenStart) / 1000;
        acc.hiddenMs += gap;
        acc.hiddenGaps.push(gap);
        acc.hiddenStart = null;
      }
    };
    const handleVisibility = () => {
      if (!isMountedRef.current) return;
      if (document.hidden) markHidden();
      else markVisible();
    };
    const handleBlur = () => {
      if (!isMountedRef.current) return;
      markHidden();
    };
    const handleFocus = () => {
      if (!isMountedRef.current) return;
      markVisible();
    };
    const handlePageHide = () => {
      markHidden();
      flush();
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isMountedRef.current) return;
      const acc = accRef.current;
      const now = performance.now();

      if (e.key === "Backspace") {
        acc.backspaceCount++;
        acc.errorCount++;
      } else if (e.key.length === 1) {
        acc.totalChars++;
      }

      acc.keyPressCount++;

      if (acc.lastKeyTime > 0) {
        const flightTime = now - acc.lastKeyTime;
        if (flightTime < 5000) acc.flightTimes.push(flightTime);
      }
      acc.lastKeyTime = now;
      keyDownTimeRef.current.set(e.key, now);
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (!isMountedRef.current) return;
      const downTime = keyDownTimeRef.current.get(e.key);
      if (downTime) {
        const holdTime = performance.now() - downTime;
        if (holdTime < 3000) accRef.current.holdTimes.push(holdTime);
        keyDownTimeRef.current.delete(e.key);
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isMountedRef.current) return;
      const now = performance.now();
      const acc = accRef.current;

      if (now - mouseMoveThrottleRef.current < 50) return;
      mouseMoveThrottleRef.current = now;

      const last = lastMouseRef.current;
      if (last) {
        const dt = (now - last.t) / 1000;
        const dx = e.clientX - last.x;
        const dy = e.clientY - last.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dt > 0) {
          const speed = dist / dt;
          if (speed < 5000) acc.mouseSpeeds.push(speed);
        }
      }
      lastMouseRef.current = { x: e.clientX, y: e.clientY, t: now };
      acc.mouseMoves.push({ x: e.clientX, y: e.clientY, t: now });
      if (acc.mouseMoves.length > 500) acc.mouseMoves = acc.mouseMoves.slice(-200);
    };

    const handleClick = (e: MouseEvent) => {
      if (!isMountedRef.current) return;
      accRef.current.clickTimestamps.push(performance.now());
      if (accRef.current.clickTimestamps.length > 200) {
        accRef.current.clickTimestamps = accRef.current.clickTimestamps.slice(-100);
      }
    };

    const handleScroll = () => {
      if (!isMountedRef.current) return;
      const acc = accRef.current;
      const now = performance.now();
      const currentY = window.scrollY || window.pageYOffset;

      if (acc.lastScrollTime > 0) {
        const dt = (now - acc.lastScrollTime) / 1000;
        if (dt > 0) {
          const velocity = Math.abs(currentY - acc.lastScrollY) / dt;
          if (velocity < 20000) acc.scrollVelocities.push(velocity);
        }
      }
      acc.lastScrollY = currentY;
      acc.lastScrollTime = now;
    };

    window.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("blur", handleBlur);
    window.addEventListener("focus", handleFocus);
    window.addEventListener("pagehide", handlePageHide);
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    window.addEventListener("click", handleClick, { passive: true });
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      isMountedRef.current = false;
      clearInterval(flushTimer);
      window.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("blur", handleBlur);
      window.removeEventListener("focus", handleFocus);
      window.removeEventListener("pagehide", handlePageHide);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("click", handleClick);
      window.removeEventListener("scroll", handleScroll);
      flush();
    };
  }, [paused, wsSend, userId, windowMs, flush]);

  return { flush };
}
