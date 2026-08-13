"""Parity test: desktop agent feature math must match the browser collector.

Fixture is the same synthetic window as
frontend/src/lib/features.test.ts — expected values are asserted there and
here. Units: hold/flight/pause ms, speeds px/s, rates per min (clamped ≥1).
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent import WindowFeatures  # noqa: E402

T0 = 1_700_000_000_000
T1 = T0 + 30_000


def build_window():
    w = WindowFeatures(T0)
    # keys → hold [80,60,90,70,120], flight [100,150,3750] (6000 dropped)
    for press, hold in [(0, 80), (100, 60), (250, 90), (4000, 70), (10000, 120)]:
        w.add_key(T0 + press, T0 + press + hold, "alpha")
    # clicks 200,300,5000 → rage pair at 200/300
    for t in (200, 300, 5000):
        w.add_click(T0 + t, 10, 10, "left")
    # moves → speeds [50,100], direction changes 1
    for x, y, t in [(0, 0, 0), (100, 0, 1000), (50, 0, 2000), (50, 100, 3000)]:
        w.add_mouse_move(T0 + t, x, y)
    # scrolls → velocities [200,300]
    w.add_scroll(T0 + 1000, 200)
    w.add_scroll(T0 + 1500, 100)
    w.add_scroll(T0 + 2000, 150)
    # app switches → 3, gaps [15000, 5000]
    for t in (5000, 20000, 25000):
        w.add_app_switch(T0 + t, "a" * 16)
    return w


def test_parity_with_browser_features():
    f = WindowFeatures.compute(build_window(), T0, T1)
    assert f["hold_time_mean"] == 84
    assert f["hold_time_median"] == 80
    assert math.isclose(f["hold_time_std"], 23.0217, abs_tol=0.01)
    assert math.isclose(f["flight_time_mean"], 1333.3333, abs_tol=0.01)
    assert f["typing_speed_wpm"] == 2
    assert f["error_rate"] == 0
    assert f["pause_frequency"] == 1
    assert f["pause_duration_mean"] == 3750
    assert f["burst_length_mean"] == 2
    assert math.isclose(f["rhythm_entropy"], 0.9183, abs_tol=0.001)
    assert math.isclose(f["mouse_speed_mean"], 83.3333, abs_tol=0.01)
    assert math.isclose(f["mouse_speed_std"], 28.8675, abs_tol=0.01)
    assert math.isclose(f["direction_change_rate"], 0.0333, abs_tol=0.01)
    assert f["click_count"] == 3
    assert f["rage_click_count"] == 1
    assert math.isclose(f["scroll_velocity_std"], 70.7107, abs_tol=0.01)
    assert f["tab_switch_freq"] == 3
    assert f["switch_entropy"] == 0
    assert math.isclose(f["session_fragmentation"], 0.3333, abs_tol=0.001)
    assert f["session_duration_min"] == 0.5
    assert 0 <= f["hour_of_day"] < 24
    assert 0 <= f["day_of_week"] < 7


def test_empty_window_is_zeros_not_nan():
    f = WindowFeatures.compute(WindowFeatures(T0), T0, T1)
    for k, v in f.items():
        assert not (isinstance(v, float) and math.isnan(v)), k
        assert v >= 0, k


def test_units_are_ms_for_timing_features():
    """Sanity: thresholds operate on ms — a 2s pause IS a pause."""
    w = WindowFeatures(T0)
    w.add_key(T0 + 0, T0 + 100, "alpha")
    w.add_key(T0 + 2000, T0 + 2100, "alpha")
    f = WindowFeatures.compute(w, T0, T1)
    assert f["pause_frequency"] == 1  # flight 2000ms > 1500ms
    assert f["pause_duration_mean"] == 2000
