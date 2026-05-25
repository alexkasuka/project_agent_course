from __future__ import annotations

import argparse
import textwrap
from datetime import datetime
from pathlib import Path

from src.course_agent import build_graph


DEFAULT_ASSIGNMENT = (
    "После занятия LangGraph: профессиональная оркестрация подготовить "
    "минимальный каркас агента: описать State, добавить два узла, один tool "
    "и human-in-the-loop проверку."
)


def shorten(text: str, width: int = 900) -> str:
    text = text.strip()
    if len(text) <= width:
        return text
    return text[:width].rstrip() + "\n..."


def print_section(title: str, body: str) -> None:
    print(f"\n=== {title} ===")
    print(body)


def save_homework_result(result: dict, human_decision: str) -> Path:
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"homework_result_{timestamp}.md"

    decision_text = "APPROVED" if human_decision == "approve" else "REQUEST CHANGES"
    citations = "\n".join(f"- `{source}`" for source in result.get("citations", []))
    context = "\n".join(
        f"- `{doc['source']}` score={doc['score']}: {doc['snippet']}"
        for doc in result.get("retrieved_context", [])
    )

    content = f"""# Homework Result

## Assignment

{result.get("assignment", "").strip()}

## Draft Solution

{result.get("draft_solution", "").strip()}

## Human Review

{result.get("review_request", "").strip()}

## Human Decision

{decision_text}

## Sources

{citations or "No citations."}

## Retrieved Context

{context or "No context found."}

## Run Metadata

- model_used: `{result.get("model_used", "unknown")}`
- risk_flags: `{", ".join(result.get("risk_flags", [])) or "none"}`
"""
    path.write_text(content, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Show assignment execution and human handoff.")
    parser.add_argument("--assignment", default=DEFAULT_ASSIGNMENT)
    parser.add_argument("--assignment-path", default="")
    parser.add_argument(
        "--human-decision",
        choices=["approve", "changes"],
        default="approve",
        help="Simulated human review result.",
    )
    args = parser.parse_args()

    input_state = {
        "user_goal": "Подготовить черновик решения перед ручной проверкой.",
    }
    if args.assignment_path:
        input_state["assignment_path"] = args.assignment_path
    else:
        input_state["assignment"] = args.assignment

    print_section("1. Assignment Input", args.assignment_path or args.assignment)

    graph = build_graph()
    result = graph.invoke(input_state)

    assignment_source = result.get("assignment_source")
    if assignment_source:
        print_section("2. Loaded Assignment File", assignment_source)

    context = "\n".join(
        f"- {doc['source']} | score={doc['score']}" for doc in result.get("retrieved_context", [])
    )
    print_section("3. Tool Execution: search_knowledge_base", context or "No course context found.")

    model_used = result.get("model_used", "unknown")
    draft = shorten(result.get("draft_solution", ""))
    print_section("4. Draft Solution", f"model_used: {model_used}\n\n{draft}")

    print_section("5. Human Handoff", result.get("review_request", "No review request produced."))

    if args.human_decision == "approve":
        decision = (
            "Human decision: APPROVED\n"
            "Next action: сохранить черновик как финальную версию или отправить в форму."
        )
    else:
        decision = (
            "Human decision: REQUEST CHANGES\n"
            "Next action: вернуть черновик в доработку с комментариями человека."
        )
    print_section("6. Simulated Human Decision", decision)

    citations = "\n".join(f"- {source}" for source in result.get("citations", []))
    print_section("7. Citations", citations or "No citations.")

    flags = ", ".join(result.get("risk_flags", [])) or "none"
    print_section("8. Final State Summary", textwrap.dedent(f"""
        risk_flags: {flags}
        has_draft: {bool(result.get("draft_solution"))}
        has_handoff: {bool(result.get("review_request"))}
    """).strip())

    output_path = save_homework_result(result, args.human_decision)
    print_section("9. Saved Homework Artifact", str(output_path))


if __name__ == "__main__":
    main()
