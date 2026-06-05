#!/usr/bin/env python3
"""Analyze benchmark results to identify failure patterns."""

import json
from pathlib import Path

results_path = Path(__file__).parent / "results.json"
encs = ["utf-8", "gbk", "gb18030"]
raw = results_path.read_bytes()
for enc in encs:
    try:
        data = json.loads(raw.decode(enc))
        break
    except (UnicodeDecodeError, json.JSONDecodeError):
        continue
else:
    data = json.loads(raw.decode("utf-8", errors="replace"))
results = data["results"]

print("=" * 70)
print("FAILURE ANALYSIS — Low-scoring cases")
print("=" * 70)

low = [r for r in results if r["score"] < 0.5]
low.sort(key=lambda x: x["score"])

for r in low[:10]:
    print(f"\n[{r['score']:.2f}] {r['id']} ({r['fault_type']})")
    print(f"  GT:  {r['ground_truth']}")
    print(f"  OUT: {r['model_output'][:200]}")
    print("  " + "-" * 60)

print(f"\n\nTotal low-scoring (<0.5): {len(low)}/{len(results)}")

print("\n\n" + "=" * 70)
print("PATTERN SUMMARY")
print("=" * 70)

patterns = {
    "missed_service": 0,
    "missed_specific_file": 0,
    "general_vague": 0,
    "wrong_cause": 0,
    "partial_correct": 0,
}

for r in low:
    gt = r["ground_truth"].lower()
    out = r["model_output"].lower()
    svc = r.get("service", "").lower()

    if svc not in out and svc:
        patterns["missed_service"] += 1

    if len(out.split()) < 15:
        patterns["general_vague"] += 1

    correct_keywords = ["pipeline", "cache", "query", "null", "timeout", "log", "config",
                        "certificate", "partition", "deploy", "regression", "memory"]
    found = sum(1 for kw in correct_keywords if kw in out and kw in gt)
    if found >= 2:
        patterns["partial_correct"] += 1
    elif found == 0:
        patterns["wrong_cause"] += 1

for k, v in patterns.items():
    print(f"  {k:25s}: {v}")
