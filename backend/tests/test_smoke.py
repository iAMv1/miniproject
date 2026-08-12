import os

os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
os.environ.setdefault("ALLOWED_ORIGINS", "http://testserver")

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_is_public_and_reports_model_state():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["model_loaded"], bool)
    assert "version" in body


def test_inference_requires_authentication():
    response = client.post("/api/v1/inference", json={"features": {}})
    assert response.status_code == 401


def test_history_requires_authentication():
    response = client.get("/api/v1/history")
    assert response.status_code == 401
