"""MindPulse — Desktop agent pairing.

Stores Supabase project URL, public anon key, and the user's refresh token in
config.json (same folder). The refresh token is a long-lived credential —
treat it like a password. Get it from the web app's /privacy page
(Desktop agent pairing card). It is auto-rotated by the agent.

Usage:
    python pair.py --refresh-token <token>
    python pair.py --url https://<ref>.supabase.co --anon-key <key> --refresh-token <token>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"


def main() -> int:
    p = argparse.ArgumentParser(description="Pair MindPulse desktop agent")
    p.add_argument("--url", default="https://lqpwjxhtziviehosqcbd.supabase.co")
    p.add_argument("--anon-key", required=True, help="NEXT_PUBLIC_SUPABASE_ANON_KEY from the web app")
    p.add_argument("--refresh-token", required=True, help="refresh token from /privacy page")
    args = p.parse_args()

    cfg = {"supabase_url": args.url, "anon_key": args.anon_key, "refresh_token": args.refresh_token}
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"✅ paired → {CONFIG_PATH}")
    print("   run: python agent.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
