from __future__ import annotations

import argparse
import json

from src.course_agent.runner import run_assignment_agent, summarize_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the assignment assistant.")
    parser.add_argument("--assignment", default="", help="Assignment text.")
    parser.add_argument("--assignment-path", default="", help="Path to a PDF, Markdown, or ipynb assignment file.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for saved Markdown results.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable run summary.")
    parser.add_argument("--verbose", action="store_true", help="Print retrieved sources and state flags.")
    parser.add_argument(
        "--human-decision",
        choices=["approve", "changes"],
        default="approve",
        help="Human review result to write into the output artifact.",
    )
    args = parser.parse_args()

    if not args.assignment and not args.assignment_path:
        parser.error("Provide --assignment or --assignment-path")

    result, output_path = run_assignment_agent(
        assignment=args.assignment,
        assignment_path=args.assignment_path,
        human_decision=args.human_decision,
        output_dir=args.output_dir,
    )

    summary = summarize_run(result, output_path)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    print(f"Saved result: {summary['output_path']}")
    print(f"Model used: {summary['model_used']}")
    print(f"Risk flags: {', '.join(summary['risk_flags']) or 'none'}")
    if summary.get("langfuse_trace_id"):
        print(f"LangFuse trace: {summary['langfuse_trace_id']}")

    if args.verbose:
        print(f"Citations: {summary['citations_count']}")
        for source in result.get("citations", []):
            print(f"- {source}")


if __name__ == "__main__":
    main()
