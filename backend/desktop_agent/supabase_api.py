"""MindPulse — Desktop agent: Supabase API client (thin, httpx-only).

No FastAPI, no SDK: direct REST calls with the user's session JWT.
Tokens are auto-refreshed from config.json (pair.py writes it).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

CONFIG_PATH = Path(__file__).parent / "config.json"


class SupabaseAPIError(RuntimeError):
    pass


def load_config() -> Dict[str, str]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            "config.json missing. Run: python pair.py --refresh-token <token>"
        )
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for k in ("supabase_url", "anon_key", "refresh_token"):
        if not cfg.get(k):
            raise RuntimeError(f"config.json missing '{k}'")
    return cfg


class SupabaseAPI:
    def __init__(self, cfg: Dict[str, str]):
        self.url = cfg["supabase_url"].rstrip("/")
        self.anon = cfg["anon_key"]
        self._refresh_token = cfg["refresh_token"]
        self._access_token: Optional[str] = None
        self._client = httpx.Client(timeout=30)

    # ── session ─────────────────────────────────────────────────────────
    def _refresh(self) -> None:
        r = self._client.post(
            f"{self.url}/auth/v1/token",
            params={"grant_type": "refresh_token"},
            headers={"apikey": self.anon, "Content-Type": "application/json"},
            json={"refresh_token": self._refresh_token},
        )
        if r.status_code != 200:
            raise SupabaseAPIError(
                f"token refresh failed ({r.status_code}): {r.text[:200]}"
            )
        body = r.json()
        self._access_token = body["access_token"]
        self._refresh_token = body["refresh_token"]
        # persist rotated refresh token
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        cfg["refresh_token"] = self._refresh_token
        CONFIG_PATH.write_text(
            json.dumps(cfg, indent=2), encoding="utf-8"
        )

    def _auth_headers(self) -> Dict[str, str]:
        if not self._access_token:
            self._refresh()
        return {"apikey": self.anon, "Authorization": f"Bearer {self._access_token}"}

    def _call(self, method: str, path: str, **kw) -> Any:
        for attempt in range(2):
            r = self._client.request(method, f"{self.url}{path}", headers=self._auth_headers(), **kw)
            if r.status_code == 401 and attempt == 0:
                self._access_token = None  # force refresh once
                continue
            if r.status_code >= 400:
                raise SupabaseAPIError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
            return r.json() if r.text else None
        raise SupabaseAPIError("auth retry exhausted")

    # ── inference ───────────────────────────────────────────────────────
    def infer(self, features: Dict[str, float]) -> Dict[str, Any]:
        return self._call(
            "POST",
            "/functions/v1/infer",
            json={"features": features},
            headers={"Content-Type": "application/json"},
        )

    # ── writes (RLS scopes to the user JWT) ─────────────────────────────
    def insert_stress_history(self, row: Dict[str, Any]) -> None:
        self._call("POST", "/rest/v1/stress_history", json=row)

    def insert_focus_snapshot(self, row: Dict[str, Any]) -> None:
        self._call("POST", "/rest/v1/focus_snapshots", json=row)

    def insert_telemetry(self, rows: List[Dict[str, Any]]) -> None:
        if rows:
            self._call("POST", "/rest/v1/telemetry_events", json=rows)

    def prune_stress_history(self, user_id: str, older_than_days: int = 90) -> None:
        cutoff = time.time() - older_than_days * 86400
        self._call(
            "DELETE",
            "/rest/v1/stress_history",
            params={
                "user_id": f"eq.{user_id}",
                "created_at": f"lt.{time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(cutoff))}",
            },
        )

    def close(self) -> None:
        self._client.close()

    def user_id(self) -> str:
        """Decode sub (user id) from the current access token."""
        import base64
        import json as _json
        token = self._access_token or ""
        if not token:
            self._refresh()
            token = self._access_token or ""
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            claims = _json.loads(base64.urlsafe_b64decode(payload))
            sub = claims.get("sub")
            if sub:
                return str(sub)
        except Exception:
            pass
        raise SupabaseAPIError("cannot determine user id from session")
