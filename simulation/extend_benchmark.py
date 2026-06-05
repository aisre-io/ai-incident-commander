#!/usr/bin/env python3
"""
P0-6: Extend the simulation benchmark to cover all 10 fault types.
Runs 2 samples per fault type for the 8 types missing from results.json
(slow_query, null_pointer, dep_timeout, disk_full, network_partition,
cert_expiry, config_error, deploy_regression), and merges into
results.json. Preserves the existing cpu_spike + memory_leak baseline.

Usage: python simulation/extend_benchmark.py
"""
import json
import sys
import time
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from openai import OpenAI
from app.config import get_settings
from simulation.evaluate import (
    build_rca_prompt,
    call_llm,
    judge_with_llm,
    load_dataset,
)

settings = get_settings()
SIM_DIR = Path(__file__).parent
RESULTS_PATH = SIM_DIR / "results.json"
BASELINE_PATH = SIM_DIR / "results_baseline.json"

MISSING_TYPES = [
    "slow_query",
    "null_pointer",
    "dep_timeout",
    "disk_full",
    "network_partition",
    "cert_expiry",
    "config_error",
    "deploy_regression",
]
SAMPLES_PER_TYPE = 2


def run_missing_evaluation() -> list[dict]:
    incidents = load_dataset()
    by_type: dict[str, list[dict]] = {}
    for inc in incidents:
        by_type.setdefault(inc["fault_type"], []).append(inc)

    new_results: list[dict] = []
    for ft in MISSING_TYPES:
        samples = by_type.get(ft, [])[:SAMPLES_PER_TYPE]
        if not samples:
            print(f"  [SKIP] {ft} — no samples in dataset")
            continue

        for inc in samples:
            print(f"  [RUN ] {inc['id']} ({ft})... ", end="", flush=True)
            system, user = build_rca_prompt(inc)
            try:
                start = time.time()
                output = call_llm(system, user, use_flash=True)
                elapsed = time.time() - start
                score = judge_with_llm(inc["ground_truth"], output)
            except Exception as e:
                print(f"FAILED: {e}")
                new_results.append({
                    "id": inc["id"],
                    "fault_type": ft,
                    "service": inc["service"],
                    "model_output": "",
                    "ground_truth": inc["ground_truth"],
                    "score": 0.0,
                    "latency": 0,
                    "error": str(e),
                })
                continue

            verdict = "PASS" if score >= 0.7 else "FAIL"
            print(f"{verdict} (score={score:.2f}, {elapsed:.1f}s)")
            new_results.append({
                "id": inc["id"],
                "fault_type": ft,
                "service": inc["service"],
                "model_output": output,
                "ground_truth": inc["ground_truth"],
                "score": round(score, 4),
                "latency": round(elapsed, 2),
            })

    return new_results


def merge_results(new_results: list[dict]) -> dict:
    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    elif RESULTS_PATH.exists():
        baseline = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        BASELINE_PATH.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  [INFO] Preserved baseline to {BASELINE_PATH.name}")
    else:
        baseline = {"meta": {"total": 0, "overall_accuracy": 0.0, "use_judge": True}, "results": []}

    all_results = baseline["results"] + new_results
    all_scores = [r["score"] for r in all_results if "score" in r]
    overall = mean(all_scores) if all_scores else 0.0

    by_type: dict[str, list[float]] = {}
    for r in all_results:
        by_type.setdefault(r["fault_type"], []).append(r.get("score", 0.0))

    print("\n" + "=" * 60)
    print("EXTENDED RCA BENCHMARK (10 fault types)")
    print("=" * 60)
    print(f"Total samples:   {len(all_results)}")
    print(f"Overall accuracy:{overall:.2%}")
    print(f"Pass rate (>=0.7): {sum(1 for s in all_scores if s >= 0.7)}/{len(all_scores)}")
    print("\n--- By Fault Type ---")
    for ft, sc in sorted(by_type.items()):
        avg = mean(sc)
        p = sum(1 for s in sc if s >= 0.7)
        bar = "#" * int(avg * 20) + "-" * (20 - int(avg * 20))
        print(f"  {ft:22s} {bar} {avg:.2%} ({p}/{len(sc)})")

    worst = [r for r in all_results if r.get("score", 1.0) < 0.4]
    if worst:
        print("\n--- Worst Cases (score < 0.4) ---")
        for r in worst[:5]:
            print(f"  {r['id']} score={r.get('score', 0):.2f}")
            print(f"    GT:  {r.get('ground_truth', '')[:80]}...")
            print(f"    OUT: {r.get('model_output', '')[:80]}...")

    return {
        "meta": {
            "total": len(all_results),
            "overall_accuracy": round(overall, 4),
            "use_judge": True,
            "by_type": {ft: {"avg": round(mean(sc), 4), "count": len(sc)} for ft, sc in by_type.items()},
        },
        "results": all_results,
    }


def main():
    print(f"Extending benchmark with 8 missing fault types x {SAMPLES_PER_TYPE} samples = {len(MISSING_TYPES) * SAMPLES_PER_TYPE} new runs\n")
    new_results = run_missing_evaluation()
    merged = merge_results(new_results)
    RESULTS_PATH.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
