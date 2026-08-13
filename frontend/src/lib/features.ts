/** MindPulse — pure feature computation (shared by browser collector, tests,
 *  and the desktop agent spec). Units match the trained model:
 *  hold/flight/pause in MILLISECONDS, speeds in px/s, rates per second/minute. */

export interface FeatureAccumulator {
  holdTimes: number[];
  flightTimes: number[];
  keyPressCount: number;
  errorCount: number;
  backspaceCount: number;
  totalChars: number;
  mouseMoves: { x: number; y: number; t: number }[];
  mouseSpeeds: number[];
  clickTimestamps: number[];
  rageClickWindows: number[];
  scrollVelocities: number[];
  lastKeyTime: number;
  lastScrollY: number;
  lastScrollTime: number;
  windowStart: number;
  tabSwitches: number;
  hiddenStart: number | null;
  hiddenMs: number;
  hiddenGaps: number[];
}

export function createAccumulator(now = Date.now()): FeatureAccumulator {
  return {
    holdTimes: [],
    flightTimes: [],
    keyPressCount: 0,
    errorCount: 0,
    backspaceCount: 0,
    totalChars: 0,
    mouseMoves: [],
    mouseSpeeds: [],
    clickTimestamps: [],
    rageClickWindows: [],
    scrollVelocities: [],
    lastKeyTime: 0,
    lastScrollY: 0,
    lastScrollTime: 0,
    windowStart: now,
    tabSwitches: 0,
    hiddenStart: null,
    hiddenMs: 0,
    hiddenGaps: [],
  };
}

export function computeShannonEntropy(values: number[]): number {
  if (values.length < 3) return 0;
  const bins = 10;
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return 0;
  const binWidth = (max - min) / bins;
  const counts = new Array(bins).fill(0);
  for (const v of values) {
    const idx = Math.min(Math.floor((v - min) / binWidth), bins - 1);
    counts[idx]++;
  }
  const n = values.length;
  let entropy = 0;
  for (const c of counts) {
    if (c > 0) {
      const p = c / n;
      entropy -= p * Math.log2(p);
    }
  }
  return entropy;
}

export function countDirectionChanges(moves: { x: number; y: number; t: number }[]): number {
  if (moves.length < 3) return 0;
  let changes = 0;
  for (let i = 2; i < moves.length; i++) {
    const dx1 = moves[i - 1].x - moves[i - 2].x;
    const dy1 = moves[i - 1].y - moves[i - 2].y;
    const dx2 = moves[i].x - moves[i - 1].x;
    const dy2 = moves[i].y - moves[i - 1].y;
    if ((dx1 > 0 && dx2 < 0) || (dx1 < 0 && dx2 > 0) || (dy1 > 0 && dy2 < 0) || (dy1 < 0 && dy2 > 0)) {
      changes++;
    }
  }
  return changes;
}

export function round(v: number, d: number) {
  const f = Math.pow(10, d);
  return Math.round(v * f) / f;
}

export function computeFeatures(acc: FeatureAccumulator, nowMs: number = Date.now()) {
  const windowSec = Math.max(1, (nowMs - acc.windowStart) / 1000);

  const holdMean = acc.holdTimes.length > 0 ? acc.holdTimes.reduce((a, b) => a + b, 0) / acc.holdTimes.length : 0;
  const holdStd = acc.holdTimes.length > 1
    ? Math.sqrt(acc.holdTimes.reduce((s, v) => s + (v - holdMean) ** 2, 0) / (acc.holdTimes.length - 1))
    : 0;
  const holdMedian = acc.holdTimes.length > 0
    ? [...acc.holdTimes].sort((a, b) => a - b)[Math.floor(acc.holdTimes.length / 2)]
    : 0;

  const flightMean = acc.flightTimes.length > 0 ? acc.flightTimes.reduce((a, b) => a + b, 0) / acc.flightTimes.length : 0;
  const flightStd = acc.flightTimes.length > 1
    ? Math.sqrt(acc.flightTimes.reduce((s, v) => s + (v - flightMean) ** 2, 0) / (acc.flightTimes.length - 1))
    : 0;

  const wpm = acc.totalChars > 0 ? (acc.totalChars / 5) / (windowSec / 60) : 0;
  const errorRate = acc.totalChars > 0 ? acc.errorCount / acc.totalChars : 0;
  const pauseCount = acc.flightTimes.filter((t) => t > 1500).length;
  const pauseMean = acc.flightTimes.filter((t) => t > 1500).reduce((a, b) => a + b, 0) / Math.max(1, pauseCount);

  const burstLengths: number[] = [];
  let currentBurst = 0;
  for (const ft of acc.flightTimes) {
    if (ft < 500) currentBurst++;
    else { if (currentBurst > 1) burstLengths.push(currentBurst); currentBurst = 0; }
  }
  if (currentBurst > 1) burstLengths.push(currentBurst);
  const burstMean = burstLengths.length > 0 ? burstLengths.reduce((a, b) => a + b, 0) / burstLengths.length : 0;

  const rhythmEntropy = computeShannonEntropy(acc.flightTimes);

  const mouseMean = acc.mouseSpeeds.length > 0 ? acc.mouseSpeeds.reduce((a, b) => a + b, 0) / acc.mouseSpeeds.length : 0;
  const mouseStd = acc.mouseSpeeds.length > 1
    ? Math.sqrt(acc.mouseSpeeds.reduce((s, v) => s + (v - mouseMean) ** 2, 0) / (acc.mouseSpeeds.length - 1))
    : 0;

  const directionChanges = countDirectionChanges(acc.mouseMoves);

  const totalClicks = acc.clickTimestamps.length;

  let rageClicks = 0;
  for (let i = 1; i < acc.clickTimestamps.length; i++) {
    if (acc.clickTimestamps[i] - acc.clickTimestamps[i - 1] < 400) rageClicks++;
  }

  const scrollStd = acc.scrollVelocities.length > 1
    ? Math.sqrt(acc.scrollVelocities.reduce((s, v) => s + (v - (acc.scrollVelocities.reduce((a, b) => a + b, 0) / acc.scrollVelocities.length)) ** 2, 0) / (acc.scrollVelocities.length - 1))
    : 0;

  const now = new Date(nowMs);
  const hourOfDay = now.getHours() + now.getMinutes() / 60;
  const dayOfWeek = now.getDay();

  const hiddenShare = Math.min(1, acc.hiddenMs / 1000 / windowSec);

  return {
    hold_time_mean: round(holdMean, 4),
    hold_time_std: round(holdStd, 4),
    hold_time_median: round(holdMedian, 4),
    flight_time_mean: round(flightMean, 4),
    flight_time_std: round(flightStd, 4),
    typing_speed_wpm: round(Math.min(wpm, 200), 2),
    error_rate: round(Math.min(errorRate, 1), 4),
    pause_frequency: round(pauseCount / Math.max(1, windowSec / 60), 2),
    pause_duration_mean: round(pauseMean, 4),
    burst_length_mean: round(burstMean, 2),
    rhythm_entropy: round(rhythmEntropy, 4),
    mouse_speed_mean: round(mouseMean, 2),
    mouse_speed_std: round(mouseStd, 2),
    direction_change_rate: round(directionChanges / Math.max(1, windowSec), 2),
    click_count: totalClicks,
    rage_click_count: rageClicks,
    scroll_velocity_std: round(scrollStd, 2),
    tab_switch_freq: round(acc.tabSwitches / Math.max(1, windowSec / 60), 2),
    switch_entropy: round(computeShannonEntropy(acc.hiddenGaps), 4),
    session_fragmentation: round(hiddenShare, 4),
    hour_of_day: round(hourOfDay, 2),
    day_of_week: dayOfWeek,
    session_duration_min: round(windowSec / 60, 2),
  };
}
