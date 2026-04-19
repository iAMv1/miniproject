"""Reality test: All backend endpoints with real data."""
import os, sys

os.environ["SUPABASE_SERVICE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImloYWFxdW1kZ2Rnc3Z5YWl5Z2dzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjQ0MDA1MiwiZXhwIjoyMDkyMDE2MDUyfQ.ChQ-dGPcUFUCVq80qEpDlUByRqdHW-kRP7IBb8fqI5I"
os.environ["GEMINI_API_KEY"] = "AIzaSyB6oQmeWMb1k18-mZwqyX3ZqLdtUCdrUMQ"
os.environ["COMPOSIO_API_KEY"] = "ak_J95Z2vGUrD0RcJxFn4JF"

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

passed = 0
failed = 0

def check(name, status, data=None):
    global passed, failed
    if status == 200:
        passed += 1
        print(f"  PASS: {name} ({status})")
    else:
        failed += 1
        print(f"  FAIL: {name} ({status}) - {data}")

print("=" * 60)
print("REALITY TEST: All Backend Endpoints")
print("=" * 60)

# 1. Health
r = client.get("/api/v1/health")
check("Health", r.status_code, r.json())

# 2. Signup (use unique username to avoid conflicts)
import time
unique_suffix = str(int(time.time()))
r = client.post("/api/v1/auth/signup", json={
    "email": f"reality{unique_suffix}@test.com",
    "username": f"realitytest{unique_suffix}",
    "password": "testpass123",
})
# If user exists, try login
if r.status_code == 409:
    r = client.post("/api/v1/auth/login", json={
        "email_or_username": "realitytest",
        "password": "testpass123",
    })
check("Signup/Login", r.status_code)
if r.status_code != 200:
    print(f"\nSignup failed, cannot continue: {r.json()}")
    sys.exit(1)

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Chat session create
r = client.post("/api/v1/chat/sessions", headers=headers, params={"title": "Reality Test"})
check("Create Chat Session", r.status_code, r.json())
session_id = r.json().get("session", {}).get("id") if r.status_code == 200 else None

# 4. Chat sessions list
r = client.get("/api/v1/chat/sessions", headers=headers)
check("List Chat Sessions", r.status_code)

# 5. Chat messages (empty is OK)
if session_id:
    r = client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=headers)
    check("Get Chat Messages", r.status_code)

# 6. Wellness checkin
r = client.post("/api/v1/wellness/checkin", headers=headers, json={
    "energy_level": "medium",
    "sleep_quality": "good",
    "note": "Reality test check-in",
})
check("Wellness Checkin", r.status_code, r.json())

# 7. Wellness checkins list
r = client.get("/api/v1/wellness/checkins", headers=headers, params={"days": 7})
check("Wellness Checkins List", r.status_code)

# 8. Today checkin
r = client.get("/api/v1/wellness/today", headers=headers)
check("Today Checkin", r.status_code)

# 9. Wellness journal
r = client.get("/api/v1/wellness/journal", headers=headers)
check("Wellness Journal", r.status_code)

# 10. Weekly reflection
r = client.get("/api/v1/wellness/weekly", headers=headers)
check("Weekly Reflection", r.status_code)

# 11. Focus state
r = client.get("/api/v1/focus/state", headers=headers)
check("Focus State", r.status_code)

# 12. Distraction shield
r = client.get("/api/v1/focus/shield", headers=headers)
check("Get Shield", r.status_code)

# 13. Toggle shield
r = client.post("/api/v1/focus/shield", headers=headers, json={"enabled": True})
check("Toggle Shield ON", r.status_code, r.json())

r = client.post("/api/v1/focus/shield", headers=headers, json={"enabled": False})
check("Toggle Shield OFF", r.status_code)

# 14. Energy forecast
r = client.get("/api/v1/focus/forecast", headers=headers)
check("Energy Forecast", r.status_code)

# 15. ML self-report
r = client.post("/api/v1/ml/self-report", headers=headers, json={
    "label": "MILD",
    "features": {
        "hold_time_mean": 120, "hold_time_std": 25, "typing_speed_wpm": 45,
        "error_rate": 0.12, "rage_click_count": 2, "direction_change_rate": 0.5,
        "session_fragmentation": 0.5, "tab_switch_freq": 8, "pause_frequency": 2.5,
        "rhythm_entropy": 3.2, "mouse_speed_std": 150, "click_count": 20,
    },
    "model_prediction": "NEUTRAL",
    "model_confidence": 0.6,
})
check("ML Self-Report", r.status_code, r.json())

# 16. ML dataset stats
r = client.get("/api/v1/ml/dataset-stats", headers=headers)
check("ML Dataset Stats", r.status_code, r.json())

# 17. ML should-ask-feedback
r = client.post("/api/v1/ml/should-ask-feedback", headers=headers, json={
    "score": 70.0,
    "confidence": 0.4,
    "model_score": 75.0,
    "heuristic_score": 40.0,
})
check("ML Should Ask Feedback", r.status_code, r.json())

# 18. Inference (full 23 features)
features = {
    "hold_time_mean": 120.0, "hold_time_std": 25.0, "hold_time_median": 115.0,
    "flight_time_mean": 150.0, "flight_time_std": 80.0, "typing_speed_wpm": 45.0,
    "error_rate": 0.12, "pause_frequency": 2.5, "pause_duration_mean": 3000.0,
    "burst_length_mean": 15.0, "rhythm_entropy": 3.2, "mouse_speed_mean": 200.0,
    "mouse_speed_std": 150.0, "direction_change_rate": 0.5, "click_count": 20.0,
    "rage_click_count": 2.0, "scroll_velocity_std": 50.0, "tab_switch_freq": 8.0,
    "switch_entropy": 2.0, "session_fragmentation": 0.5, "hour_of_day": 10.0,
    "day_of_week": 2.0, "session_duration_min": 30.0,
}
r = client.post("/api/v1/inference", json={"features": features, "user_id": "realitytest"})
result = r.json()
check("Inference", r.status_code)
if r.status_code == 200:
    print(f"    -> score={result.get('score')}, level={result.get('level')}, "
          f"adaptive_weight={result.get('adaptive_weight')}, "
          f"lstm_adjustment={result.get('lstm_adjustment')}")

# 19. History
r = client.get("/api/v1/history", params={"user_id": "realitytest", "hours": 24})
check("History", r.status_code)

# 20. Stats
r = client.get("/api/v1/stats", params={"user_id": "realitytest"})
check("Stats", r.status_code)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if failed == 0:
    print("ALL ENDPOINTS WORKING")
else:
    print(f"{failed} ENDPOINTS FAILED")
print("=" * 60)
