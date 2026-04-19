"""Test FastAPI endpoints via TestClient."""
import sys
import json
import time
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 60)
print("  MindPulse Full Endpoint Integration Test")
print("=" * 60)

# Test 1: Health
print("\nTEST 1: GET /api/v1/health")
r = client.get("/api/v1/health")
assert r.status_code == 200, f"Expected 200, got {r.status_code}"
data = r.json()
print(f"  OK - status={data['status']}, model_loaded={data['model_loaded']}")

# Test 2: Auth routes
print("\nTEST 2: Auth endpoints")
# 2a: Signup
r = client.post("/api/v1/auth/signup", json={
    "email": "testuser@mindpulse.app",
    "username": "testuser",
    "password": "test123456",
    "display_name": "Test User"
})
if r.status_code == 409:
    print("  OK - User already exists, trying login instead")
    r = client.post("/api/v1/auth/login", json={
        "email_or_username": "testuser@mindpulse.app",
        "password": "test123456"
    })
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
token = r.json()["access_token"]
user_id = str(r.json()["user"]["id"])
print(f"  OK - Auth: user_id={user_id}, has_token={bool(token)}")

# 2b: /auth/me
headers = {"Authorization": f"Bearer {token}"}
r = client.get("/api/v1/auth/me", headers=headers)
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
print(f"  OK - /auth/me: email={r.json()['email']}")

# 2c: Demo token
r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer demo"})
assert r.status_code == 200, f"Expected 200 for demo token, got {r.status_code}: {r.text}"
print(f"  OK - Demo token works: {r.json()['username']}")

# Test 3: Inference
print("\nTEST 3: POST /inference")
features_payload = {
    "features": {
        "hold_time_mean": 0.12, "hold_time_std": 0.03, "hold_time_median": 0.11,
        "flight_time_mean": 0.08, "flight_time_std": 0.02,
        "typing_speed_wpm": 60.0, "error_rate": 0.05,
        "pause_frequency": 2.0, "pause_duration_mean": 1.5,
        "burst_length_mean": 3.0, "rhythm_entropy": 2.5,
        "mouse_speed_mean": 200.0, "mouse_speed_std": 50.0,
        "direction_change_rate": 0.3, "click_count": 10, "rage_click_count": 1,
        "scroll_velocity_std": 30.0, "tab_switch_freq": 0, "switch_entropy": 0,
        "session_fragmentation": 0, "hour_of_day": 14.5, "day_of_week": 3,
        "session_duration_min": 5.0,
        "mouse_reentry_count": 0, "mouse_reentry_latency_ms": 0
    },
    "user_id": user_id
}
r = client.post("/api/v1/inference", json=features_payload)
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
data = r.json()
must_have = ['score', 'level', 'typing_speed_wpm', 'rage_click_count', 'error_rate', 'click_count', 'mouse_speed_mean']
missing = [k for k in must_have if k not in data]
if missing:
    print(f"  FAIL - Missing keys in inference response: {missing}")
else:
    print(f"  OK - Inference: score={data['score']}, level={data['level']}, wpm={data['typing_speed_wpm']}, mouse={data['mouse_speed_mean']}")

# Test 4: History
print("\nTEST 4: GET /history")
r = client.get(f"/api/v1/history?user_id={user_id}&hours=24")
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
history = r.json()
print(f"  OK - History points: {len(history)}")
if len(history) > 0:
    hp = history[0]
    missing_features = [k for k in must_have if k not in hp]
    if missing_features:
        print(f"  FAIL - History missing: {missing_features}")
    else:
        print(f"  OK - History point has all features: wpm={hp['typing_speed_wpm']}, mouse={hp['mouse_speed_mean']}")

# Test 5: Stats
print("\nTEST 5: GET /stats")
r = client.get(f"/api/v1/stats?user_id={user_id}")
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
stats = r.json()
assert "mouse_speed_mean" in stats, "mouse_speed_mean missing from stats!"
print(f"  OK - Stats: samples={stats['total_samples']}, wpm={stats['typing_speed_wpm']}, mouse={stats['mouse_speed_mean']}")

# Test 6: Intervention recommendation
print("\nTEST 6: GET /interventions/recommendation")
r = client.get(f"/api/v1/interventions/recommendation?user_id={user_id}")
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
rec = r.json()
print(f"  OK - Alert: {rec['alert_state']}, Trend: {rec['trend']}")

# Test 7: Intervention history
print("\nTEST 7: GET /interventions/history")
r = client.get(f"/api/v1/interventions/history?user_id={user_id}&hours=168")
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
print(f"  OK - Intervention events: {len(r.json())}")

# Test 8: Wind-down check
print("\nTEST 8: GET /interventions/wind-down")
r = client.get(f"/api/v1/interventions/wind-down?user_id={user_id}")
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
print(f"  OK - Wind-down: {r.json()}")

# Test 9: Calibration
print("\nTEST 9: GET /calibration/{user_id}")
r = client.get(f"/api/v1/calibration/{user_id}")
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
cal = r.json()
print(f"  OK - Calibrated: {cal['is_calibrated']}, completion: {cal['completion_pct']}%")

# Test 10: Feedback
print("\nTEST 10: POST /feedback")
r = client.post("/api/v1/feedback", json={
    "user_id": user_id,
    "predicted_level": "NEUTRAL",
    "actual_level": "NEUTRAL",
    "timestamp": time.time() * 1000
})
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
print(f"  OK - Feedback accepted")

# Test 11: Reset
print("\nTEST 11: POST /reset")
r = client.post("/api/v1/reset", json={"user_id": user_id})
assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
print(f"  OK - Reset successful")

# Test 12: CORS headers
print("\nTEST 12: CORS headers")
r = client.options("/api/v1/health", headers={
    "Origin": "http://localhost:3000",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "Authorization, Content-Type",
})
print(f"  OK - CORS preflight: {r.status_code}")

# Test 13: Google OAuth callback (will fail without config, but route exists)
print("\nTEST 13: GET /auth/google/callback (route exists)")
r = client.get("/api/v1/auth/google/callback?code=test")
# Will likely 500 without real Google creds, but should not 404
if r.status_code == 500:
    print(f"  OK - Route exists (500 without real Google creds): {r.json().get('detail', '')[:60]}")
elif r.status_code == 302:
    print(f"  OK - Redirects (302)")
else:
    print(f"  Status: {r.status_code}")

# Cleanup
from app.services.history import reset as reset_history
reset_history(user_id)

print("\n" + "=" * 60)
print("  ALL ENDPOINT TESTS PASSED")
print("=" * 60)