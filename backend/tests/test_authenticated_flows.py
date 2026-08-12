import os
import secrets

os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
os.environ.setdefault("ALLOWED_ORIGINS", "http://testserver")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_user_headers() -> dict[str, str]:
    suffix = secrets.token_hex(6)
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"test-{suffix}@example.invalid",
            "username": f"tester_{suffix}",
            "password": "secure-test-password",
            "display_name": "Test User",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _active_feature_payload() -> dict[str, float]:
    return {
        "hold_time_mean": 0.12,
        "hold_time_std": 0.05,
        "hold_time_median": 0.11,
        "flight_time_mean": 0.18,
        "flight_time_std": 0.08,
        "typing_speed_wpm": 42,
        "error_rate": 0.02,
        "pause_frequency": 3,
        "pause_duration_mean": 1.2,
        "burst_length_mean": 6,
        "rhythm_entropy": 1.1,
        "mouse_speed_mean": 240,
        "mouse_speed_std": 70,
        "direction_change_rate": 2,
        "click_count": 8,
        "rage_click_count": 0,
        "scroll_velocity_std": 25,
        "tab_switch_freq": 2,
        "switch_entropy": 0.8,
        "session_fragmentation": 0.2,
        "hour_of_day": 12,
        "day_of_week": 2,
        "session_duration_min": 5,
    }


def test_authenticated_inference_returns_signal_context():
    headers = _create_user_headers()
    response = client.post(
        "/api/v1/inference", json={"features": _active_feature_payload()}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["signal_state"] in {"CALIBRATING", "READY", "UNAVAILABLE"}
    assert "input_quality" in body
    assert "signal_message" in body


def test_export_and_delete_cover_telemetry_and_ema_data():
    headers = _create_user_headers()
    telemetry_response = client.post(
        "/api/v1/telemetry/batch",
        json={
            "client": "browser",
            "events": [
                {"type": "key", "t": 1000, "key": "x", "down_ms": 1000, "up_ms": 1010},
                {"type": "mouse", "t": 1001, "x": 20, "y": 30, "kind": "move"},
            ],
        },
        headers=headers,
    )
    assert telemetry_response.status_code == 200, telemetry_response.text
    ema_response = client.post(
        "/api/v1/ema/checkin",
        json={"stress": 4, "fatigue": 3},
        headers=headers,
    )
    assert ema_response.status_code == 200, ema_response.text

    exported = client.get("/api/v1/privacy/export", headers=headers)
    assert exported.status_code == 200, exported.text
    body = exported.json()
    assert len(body["telemetry"]) == 2
    assert len(body["ema_checkins"]) == 1
    assert "key_hash" not in body["telemetry"][0]

    deleted = client.delete("/api/v1/privacy/data", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["account_retained"] is True

    exported_after_delete = client.get("/api/v1/privacy/export", headers=headers)
    assert exported_after_delete.status_code == 200
    assert exported_after_delete.json()["telemetry"] == []
    assert exported_after_delete.json()["ema_checkins"] == []
