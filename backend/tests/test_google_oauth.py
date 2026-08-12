import os
from urllib.parse import parse_qs, urlsplit

os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
os.environ.setdefault("ALLOWED_ORIGINS", "http://testserver")

from fastapi.testclient import TestClient

from app.api import auth_routes
from app.main import app


class StubResponse:
    def __init__(self, status_code: int, payload: dict[str, object]):
        self.status_code = status_code
        self._payload = payload
        self.text = "stub response"

    def json(self) -> dict[str, object]:
        return self._payload


def configure_google(monkeypatch) -> None:
    monkeypatch.setattr(auth_routes, "GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(auth_routes, "GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(
        auth_routes,
        "GOOGLE_REDIRECT_URI",
        "http://testserver/api/v1/auth/google/callback",
    )
    monkeypatch.setattr(
        auth_routes,
        "FRONTEND_CALLBACK_URL",
        "http://frontend.example/auth/callback",
    )


def test_google_start_issues_state_cookie_and_uses_backend_callback(monkeypatch):
    configure_google(monkeypatch)
    client = TestClient(app)

    response = client.get("/api/v1/auth/google", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    parsed = urlsplit(location)
    params = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert params["client_id"] == ["test-client-id"]
    assert params["redirect_uri"] == [
        "http://testserver/api/v1/auth/google/callback"
    ]
    assert client.cookies.get("oauth_state") == params["state"][0]


def test_google_callback_validates_state_and_hands_token_to_frontend(monkeypatch):
    configure_google(monkeypatch)
    client = TestClient(app)
    client.cookies.set("oauth_state", "matching-state")

    def fake_post(url: str, data: dict[str, str], timeout: int) -> StubResponse:
        assert url == "https://oauth2.googleapis.com/token"
        assert data["redirect_uri"] == "http://testserver/api/v1/auth/google/callback"
        assert timeout == 10
        return StubResponse(200, {"access_token": "google-access-token"})

    def fake_get(url: str, headers: dict[str, str], timeout: int) -> StubResponse:
        assert url == "https://www.googleapis.com/oauth2/v2/userinfo"
        assert headers["Authorization"] == "Bearer google-access-token"
        assert timeout == 10
        return StubResponse(
            200,
            {"id": "google-123", "email": "person@example.invalid", "name": "Person"},
        )

    monkeypatch.setattr(auth_routes.requests, "post", fake_post)
    monkeypatch.setattr(auth_routes.requests, "get", fake_get)
    monkeypatch.setattr(
        auth_routes.users,
        "create_or_login_google_user",
        lambda email, name, google_id: {
            "access_token": "mindpulse-token",
            "user": {"id": 7, "email": email, "display_name": name},
        },
    )

    response = client.get(
        "/api/v1/auth/google/callback?code=authorization-code&state=matching-state",
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = urlsplit(response.headers["location"])
    assert location.scheme == "http"
    assert location.netloc == "frontend.example"
    assert location.path == "/auth/callback"
    fragment = parse_qs(location.fragment)
    assert fragment["token"] == ["mindpulse-token"]
    assert fragment["user"] == ['{"id": 7, "email": "person@example.invalid", "display_name": "Person"}']


def test_google_callback_rejects_missing_or_mismatched_state(monkeypatch):
    configure_google(monkeypatch)
    client = TestClient(app)
    client.cookies.set("oauth_state", "expected-state")

    response = client.get(
        "/api/v1/auth/google/callback?code=authorization-code&state=wrong-state",
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or missing OAuth state parameter"


def test_google_callback_returns_provider_denial_to_frontend(monkeypatch):
    configure_google(monkeypatch)
    client = TestClient(app)

    response = client.get(
        "/api/v1/auth/google/callback?error=access_denied",
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = urlsplit(response.headers["location"])
    assert location.netloc == "frontend.example"
    assert location.path == "/auth/callback"
    assert parse_qs(location.query) == {"error": ["access_denied"]}
