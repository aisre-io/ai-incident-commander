#!/usr/bin/env python3
"""
Lark e2e validation helper.

Sends a mock PagerDuty webhook to the local FastAPI server.
After running, you should see a Lark card in your test group within 5-15s.

Prereqs:
    1. .env has DEEPSEEK_API_KEY and LARK_WEBHOOK_URL set
    2. Server is running: python run.py
    3. Lark group has a custom bot configured (webhook URL filled in .env)

Usage:
    python simulation/send_test_incident.py
    python simulation/send_test_incident.py --url http://localhost:8000
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
SAMPLE = Path(__file__).parent / "samples" / "pagerduty-incident.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000",
                        help="FastAPI base URL (default: http://127.0.0.1:8000)")
    parser.add_argument("--path", default="/webhook/pagerduty",
                        help="Webhook path (default: /webhook/pagerduty)")
    args = parser.parse_args()

    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    target = f"{args.url.rstrip('/')}{args.path}"

    print(f"Target:  {target}")
    print(f"Payload: {SAMPLE.name} ({len(json.dumps(payload))} bytes)\n")
    print("Sending... ", end="", flush=True)

    try:
        start = time.time()
        resp = httpx.post(target, json=payload, timeout=60.0)
        elapsed = time.time() - start
    except httpx.RequestError as e:
        print(f"FAILED: {e}")
        print(f"\nIs the server running? Start it with: python run.py")
        return 1

    print(f"HTTP {resp.status_code} in {elapsed:.1f}s")
    try:
        body = resp.json()
    except Exception:
        body = resp.text

    print(f"Response:\n{json.dumps(body, indent=2, ensure_ascii=False) if isinstance(body, dict) else body}\n")

    if resp.status_code < 300:
        print("OK. Check your Lark group — a critical-severity (red header) card should appear in 5-15s.")
        print("If no card: recheck LARK_WEBHOOK_URL in .env matches the bot in your Lark group settings.")
    else:
        print("Server returned an error. Check app logs for details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
