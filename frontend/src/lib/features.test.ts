import { describe, expect, it } from "vitest";
import { createAccumulator, computeFeatures } from "./features";

const T0 = 1_700_000_000_000;
const T1 = T0 + 30_000;

/** Deterministic synthetic window — the parity fixture shared with the
 *  desktop agent tests (backend/desktop_agent/tests/test_desktop_features.py). */
function buildFixture() {
  const acc = createAccumulator(T0);
  acc.holdTimes = [80, 60, 90, 70, 120];
  acc.flightTimes = [100, 150, 3750];
  acc.totalChars = 5;
  acc.errorCount = 0;
  acc.clickTimestamps = [200, 300, 5000];
  acc.mouseSpeeds = [100, 50, 100];
  acc.mouseMoves = [
    { x: 0, y: 0, t: 0 },
    { x: 100, y: 0, t: 1000 },
    { x: 50, y: 0, t: 2000 },
    { x: 50, y: 100, t: 3000 },
  ];
  acc.scrollVelocities = [200, 300];
  acc.tabSwitches = 3;
  acc.hiddenGaps = [15000, 5000];
  acc.hiddenMs = 10000;
  return acc;
}

describe("computeFeatures (parity fixture — desktop agent must match)", () => {
  it("computes the shared fixture deterministically", () => {
    const f = computeFeatures(buildFixture(), T1);
    expect(f.hold_time_mean).toBe(84);
    expect(f.hold_time_median).toBe(80);
    expect(f.hold_time_std).toBeCloseTo(23.0217, 2);
    expect(f.flight_time_mean).toBeCloseTo(1333.3333, 2);
    expect(f.typing_speed_wpm).toBe(2);
    expect(f.error_rate).toBe(0);
    expect(f.pause_frequency).toBe(1);
    expect(f.pause_duration_mean).toBe(3750);
    expect(f.burst_length_mean).toBe(2);
    expect(f.rhythm_entropy).toBeCloseTo(0.9183, 3);
    expect(f.mouse_speed_mean).toBeCloseTo(83.3333, 2);
    expect(f.mouse_speed_std).toBeCloseTo(28.8675, 2);
    expect(f.direction_change_rate).toBeCloseTo(0.0333, 2);
    expect(f.click_count).toBe(3);
    expect(f.rage_click_count).toBe(1);
    expect(f.scroll_velocity_std).toBeCloseTo(70.7107, 2);
    expect(f.tab_switch_freq).toBe(3);
    expect(f.switch_entropy).toBe(0);
    expect(f.session_fragmentation).toBeCloseTo(0.3333, 3);
    expect(f.session_duration_min).toBe(0.5);
    expect(f.hour_of_day).toBeGreaterThanOrEqual(0);
    expect(f.hour_of_day).toBeLessThan(24);
    expect(f.day_of_week).toBeGreaterThanOrEqual(0);
    expect(f.day_of_week).toBeLessThan(7);
  });

  it("empty window yields zeros, never NaN", () => {
    const f = computeFeatures(createAccumulator(T0), T1);
    for (const [k, v] of Object.entries(f)) {
      expect(Number.isNaN(v), k).toBe(false);
      expect(v).toBeGreaterThanOrEqual(0);
    }
    expect(f.typing_speed_wpm).toBe(0);
  });

  it("clamps error_rate and wpm to model bounds", () => {
    const acc = buildFixture();
    acc.totalChars = 1;
    acc.errorCount = 5;
    acc.mouseMoves = [];
    const f = computeFeatures(acc, T1);
    expect(f.error_rate).toBe(1);
  });
});
