from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.course_agent import build_graph


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * percentile_value), len(ordered) - 1)
    return ordered[index]


def case_passed(result: dict[str, Any], expected: dict[str, Any]) -> bool:
    text = "\n".join(
        [
            result.get("draft_solution", ""),
            result.get("review_request", ""),
            " ".join(result.get("citations", [])),
        ]
    ).lower()
    must_include = [item.lower() for item in expected.get("must_include", [])]
    includes_ok = all(item in text for item in must_include)

    if expected.get("must_have_citations") is True:
        citations_ok = bool(result.get("citations"))
    elif expected.get("must_have_citations") is False:
        citations_ok = True
    else:
        citations_ok = True

    expected_route = expected.get("expected_route")
    route_ok = not expected_route or result.get("context_route") == expected_route

    return includes_ok and citations_ok and route_ok


def run_benchmark(cases_path: Path, disable_model_calls: bool) -> dict[str, Any]:
    if disable_model_calls:
        os.environ["DISABLE_MODEL_CALLS"] = "1"

    graph = build_graph()
    rows = []
    latencies = []

    for case in load_cases(cases_path):
        started = time.perf_counter()
        result = graph.invoke({"assignment": case["input"], "user_goal": "benchmark"})
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        passed = case_passed(result, case["expected_output"])
        rows.append(
            {
                "id": case["id"],
                "passed": passed,
                "latency_ms": round(latency_ms, 2),
                "context_route": result.get("context_route"),
                "model_used": result.get("model_used", "unknown"),
                "citations_count": len(result.get("citations", [])),
                "risk_flags": result.get("risk_flags", []),
            }
        )

    passed_count = sum(1 for row in rows if row["passed"])
    retrieval_hits = sum(1 for row in rows if row["citations_count"] > 0)
    return {
        "cases": rows,
        "summary": {
            "total": len(rows),
            "passed": passed_count,
            "success_rate": round(passed_count / len(rows), 4) if rows else 0.0,
            "retrieval_hit_rate": round(retrieval_hits / len(rows), 4) if rows else 0.0,
            "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p95_latency_ms": round(percentile(latencies, 0.95), 2),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run assignment assistant benchmark.")
    parser.add_argument("--cases", default="benchmarks/assignment_cases.json")
    parser.add_argument("--output", default="")
    parser.add_argument("--use-model", action="store_true", help="Allow OpenRouter/Ollama model calls.")
    args = parser.parse_args()

    report = run_benchmark(Path(args.cases), disable_model_calls=not args.use_model)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
