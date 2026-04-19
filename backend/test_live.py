import requests, json

features = {
    "hold_time_mean": 0.12, "hold_time_std": 0.03, "hold_time_median": 0.11,
    "flight_time_mean": 0.08, "flight_time_std": 0.02,
    "typing_speed_wpm": 60.0, "error_rate": 0.05,
    "pause_frequency": 2.0, "pause_duration_mean": 1.5,
    "burst_length_mean": 3.0, "rhythm_entropy": 2.5,
    "mouse_speed_mean": 200.0, "mouse_speed_std": 50.0,
    "direction_change_rate": 0.3, "click_count": 10, "rage_click_count": 1,
    "scroll_velocity_std": 30.0, "tab_switch_freq": 0, "switch_entropy": 0,
    "session_fragmentation": 0, "hour_of_day": 14.5, "day_of_week": 3,
    "session_duration_min": 5.0, "mouse_reentry_count": 0, "mouse_reentry_latency_ms": 0
}

r = requests.post("http://localhost:5000/api/v1/inference", json={"features": features, "user_id": "0"}, timeout=10)
print(f"inference -> {r.status_code}")
d = r.json()
wpm = d.get("typing_speed_wpm", "MISSING")
mouse = d.get("mouse_speed_mean", "MISSING")
rage = d.get("rage_click_count", "MISSING")
print(f"  score={d['score']}, level={d['level']}, wpm={wpm}, mouse={mouse}, rage={rage}")

# Check history was stored with features
r2 = requests.get("http://localhost:5000/api/v1/history?user_id=0&hours=1", timeout=5)
print(f"history -> {r2.status_code}, points: {len(r2.json())}")
if r2.json():
    hp = r2.json()[-1]
    print(f"  last point: wpm={hp.get('typing_speed_wpm')}, mouse={hp.get('mouse_speed_mean')}, rage={hp.get('rage_click_count')}")

# Check stats
r3 = requests.get("http://localhost:5000/api/v1/stats?user_id=0", timeout=5)
print(f"stats -> {r3.status_code}")
s = r3.json()
print(f"  wpm={s.get('typing_speed_wpm')}, mouse={s.get('mouse_speed_mean')}")

print("\nALL INTEGRATION CHECKS PASSED")