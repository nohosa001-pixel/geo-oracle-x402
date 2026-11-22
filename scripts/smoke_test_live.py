"""
Live Deployment Smoke Test for geo-oracle-x402 (v3.0.0).
Verifies /health, discovery standards, free /preview, and x402 HTTP 402 challenge on a live URL.

Usage:
  python scripts/smoke_test_live.py --url https://geo-oracle-x402-xxxx.asia-northeast3.run.app
"""

from __future__ import annotations

import argparse
import sys
import httpx


def run_smoke_test(base_url: str) -> int:
    base = base_url.rstrip("/")
    checks = [
        ("GET /health", "GET", "/health", None, 200),
        ("GET /.well-known/x402.json", "GET", "/.well-known/x402.json", None, 200),
        ("GET /.well-known/agent-card.json", "GET", "/.well-known/agent-card.json", None, 200),
        ("GET /llms.txt", "GET", "/llms.txt", None, 200),
        ("GET /v1/infrastructure/catalog", "GET", "/v1/infrastructure/catalog", None, 200),
        (
            "POST /v1/infrastructure/preview",
            "POST",
            "/v1/infrastructure/preview",
            {
                "asset_id": "SMOKE-DC-01",
                "asset_type": "DATA_CENTER",
                "latitude": 37.5665,
                "longitude": 126.9780,
                "use_live_feed": True,
            },
            200,
        ),
        (
            "POST /v1/infrastructure/assess (unpaid -> 402)",
            "POST",
            "/v1/infrastructure/assess",
            {
                "asset_id": "SMOKE-DC-01",
                "asset_type": "DATA_CENTER",
                "latitude": 37.5665,
                "longitude": 126.9780,
                "use_live_feed": False,
            },
            402,
        ),
    ]

    failed = 0
    with httpx.Client(timeout=15.0) as client:
        for name, method, path, body, expected_status in checks:
            try:
                resp = client.request(method, f"{base}{path}", json=body)
                ok = resp.status_code == expected_status
                extra = ""
                if ok and path == "/v1/infrastructure/preview":
                    summary = resp.json().get("summary", {})
                    extra = (
                        f" (score={summary.get('combined_risk_score')}, "
                        f"grade={summary.get('risk_grade')}, "
                        f"confidence={summary.get('assessment_confidence')}, "
                        f"degraded={summary.get('degraded_layers')})"
                    )
                status_tag = "PASS" if ok else "FAIL"
                print(f"[{status_tag}] {name}: HTTP {resp.status_code} (expected {expected_status}){extra}")
                if not ok:
                    failed += 1
            except Exception as exc:
                print(f"[FAIL] {name}: {exc}")
                failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Smoke Test for geo-oracle-x402")
    parser.add_argument("--url", required=True, help="Deployed service base URL")
    args = parser.parse_args()
    sys.exit(run_smoke_test(args.url))
