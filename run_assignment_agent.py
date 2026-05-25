from __future__ import annotations

import argparse

from src.course_agent.runner import run_assignment_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the assignment assistant.")
    parser.add_argument("--assignment", default="", help="Assignment text.")
    parser.add_argument("--assignment-path", default="", help="Path to a PDF or ipynb assignment file.")
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
    )

    print(f"Saved result: {output_path}")
    print(f"Model used: {result.get('model_used', 'unknown')}")
    print(f"Risk flags: {', '.join(result.get('risk_flags', [])) or 'none'}")


if __name__ == "__main__":
    main()

