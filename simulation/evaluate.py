#!/usr/bin/env python3
"""
RCA accuracy benchmark — runs all simulation incidents through the LLM
and scores each result against ground truth.

Usage:
    python simulation/evaluate.py                    # Run full benchmark
    python simulation/evaluate.py --fault cpu_spike  # Single fault type
    python simulation/evaluate.py --sample 5         # First 5 incidents
    python simulation/evaluate.py --judge            # LLM-as-judge (more accurate)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from openai import OpenAI
from app.config import get_settings, get_model_for

settings = get_settings()
SIMULATION_DIR = Path(__file__).parent
DATASET_PATH = SIMULATION_DIR / "dataset.json"
RESULTS_PATH = SIMULATION_DIR / "results.json"


def load_dataset() -> list[dict]:
    raw = DATASET_PATH.read_bytes()
    for enc in ["utf-8", "gbk", "gb18030"]:
        try:
            return json.loads(raw.decode(enc))["incidents"]
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return json.loads(raw.decode("utf-8", errors="replace"))["incidents"]


def build_rca_prompt(incident: dict) -> tuple[str, str]:
    alerts_str = "\n".join(
        f"[{a['severity']}] {a['title']}: {a['description']}"
        for a in incident["alerts"]
    )
    commits_str = "\n".join(
        f"  - {c['message']} ({c['author']}, {c['files_changed']} files)"
        for c in incident["commits"]
    ) if incident.get("commits") else "  (no recent commits)"

    logs_str = "\n".join(f"  - {l}" for l in incident["logs"])

    system = (
        "You are an expert SRE root cause analysis engineer. "
        "Given alerts, git commits, and logs, identify the single most likely root cause.\n\n"
        "Analysis method:\n"
        "1. Read the error logs first — they tell you what actually broke\n"
        "2. Cross-reference with alerts to confirm the affected service\n"
        "3. Scan recent commits — the most suspicious change is the one that:\n"
        "   - Touches the same component mentioned in the error logs\n"
        "   - Was deployed shortly before the incident\n"
        "   - Has a pattern consistent with the failure (new feature = regression risk, "
        "ops change = config/network risk, dependency bump = timeout risk)\n"
        "4. Synthesize: what is the causal chain from commit → system behavior → alert?\n\n"
        "Output a concise root cause analysis in 2-3 sentences. "
        "Be specific about the file, commit, or configuration change that caused the issue."
    )

    user = f"""Analyze this incident:

Service: {incident['service']}
Severity: {incident['severity']}

ALERTS:
{alerts_str}

ERROR LOGS:
{logs_str}

RECENT COMMITS:
{commits_str}

What is the root cause?"""

    return system, user


def call_llm(system: str, user: str, model: str = "", use_flash: bool = False) -> str:
    model = model or (get_model_for("quick") if use_flash else get_model_for("rca"))
    client = OpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
    )
    return resp.choices[0].message.content or ""


def judge_with_llm(ground_truth: str, model_output: str) -> float:
    client = OpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=get_model_for("quick"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an RCA accuracy judge. Compare the ground truth root cause "
                    "with the model's analysis. Score 0.0-1.0:\n"
                    "1.0 = Perfect match (same root cause, same detail)\n"
                    "0.7 = Same root cause, missing some detail\n"
                    "0.4 = Related but wrong root cause\n"
                    "0.0 = Completely wrong\n"
                    "Output ONLY the number, nothing else."
                ),
            },
            {
                "role": "user",
                "content": f"GROUND TRUTH: {ground_truth}\n\nMODEL OUTPUT: {model_output}\n\nScore:",
            },
        ],
        temperature=0.0,
    )
    try:
        return float(resp.choices[0].message.content.strip())
    except (ValueError, AttributeError):
        return 0.0


def keyword_score(ground_truth: str, model_output: str) -> float:
    gt_lower = ground_truth.lower()
    out_lower = model_output.lower()

    keywords = set()
    for word in gt_lower.replace(",", "").replace(".", "").split():
        if len(word) > 4:
            keywords.add(word)

    matches = sum(1 for k in keywords if k in out_lower)
    if not keywords:
        return 0.0
    return matches / len(keywords)


def run_evaluation(incidents: list[dict], use_judge: bool = False, use_flash: bool = False) -> list[dict]:
    results = []
    total = len(incidents)

    for i, inc in enumerate(incidents):
        print(f"[{i+1}/{total}] {inc['id']} ({inc['fault_type']})... ", end="", flush=True)

        system, user = build_rca_prompt(inc)

        try:
            start = time.time()
            output = call_llm(system, user, use_flash=use_flash)
            elapsed = time.time() - start
        except Exception as e:
            print(f"FAILED: {e}")
            results.append({**inc, "model_output": "", "score": 0.0, "error": str(e), "latency": 0})
            continue

        if use_judge:
            score = judge_with_llm(inc["ground_truth"], output)
        else:
            score = keyword_score(inc["ground_truth"], output)

        results.append({
            "id": inc["id"],
            "fault_type": inc["fault_type"],
            "service": inc["service"],
            "model_output": output,
            "ground_truth": inc["ground_truth"],
            "score": round(score, 4),
            "latency": round(elapsed, 2),
        })

        verdict = "PASS" if score >= 0.7 else "FAIL"
        print(f"{verdict} (score={score:.2f}, {elapsed:.1f}s)")

    return results


def print_report(results: list[dict]):
    scores = [r["score"] for r in results]
    overall = mean(scores) if scores else 0.0

    print("\n" + "=" * 60)
    print("RCA BENCHMARK REPORT")
    print("=" * 60)
    print(f"Total incidents: {len(results)}")
    print(f"Overall accuracy: {overall:.2%}")
    print(f"Std deviation:   {stdev(scores):.2%}" if len(scores) > 1 else "")

    passes = sum(1 for s in scores if s >= 0.7)
    print(f"Pass rate:       {passes}/{len(results)} ({passes/len(results):.2%})")

    print("\n--- By Fault Type ---")
    by_type: dict[str, list[float]] = {}
    for r in results:
        by_type.setdefault(r["fault_type"], []).append(r["score"])

    for ft, sc in sorted(by_type.items()):
        avg = mean(sc)
        p = sum(1 for s in sc if s >= 0.7)
        bar = "#" * int(avg * 20) + "-" * (20 - int(avg * 20))
        print(f"  {ft:20s} {bar} {avg:.2%} ({p}/{len(sc)})")

    print("\n--- Worst Cases (score < 0.4) ---")
    worst = [r for r in results if r["score"] < 0.4]
    if worst:
        for r in worst[:5]:
            print(f"  {r['id']} score={r['score']:.2f}")
            print(f"    GT:  {r['ground_truth'][:80]}...")
            print(f"    OUT: {r['model_output'][:80]}...")
            print()
    else:
        print("  (none)")

    return overall


def main():
    parser = argparse.ArgumentParser(description="RCA Benchmark")
    parser.add_argument("--fault", type=str, help="Filter by fault type")
    parser.add_argument("--sample", type=int, help="Run only first N incidents")
    parser.add_argument("--judge", action="store_true", help="Use LLM-as-judge")
    parser.add_argument("--flash", action="store_true", help="Use Flash model instead of Pro for RCA")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    args = parser.parse_args()

    incidents = load_dataset()

    if args.fault:
        incidents = [i for i in incidents if i["fault_type"] == args.fault]
        print(f"Filtered to {len(incidents)} incidents: {args.fault}")

    if args.sample:
        incidents = incidents[: args.sample]
        print(f"Running first {args.sample} incidents")

    print(f"Loaded {len(incidents)} incidents from dataset\n")

    results = run_evaluation(incidents, use_judge=args.judge, use_flash=args.flash)
    overall = print_report(results)

    if args.save:
        output = {
            "meta": {"total": len(results), "overall_accuracy": round(overall, 4), "use_judge": args.judge, "use_flash": args.flash},
            "results": results,
        }
        RESULTS_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
