from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .graph import build_graph


def build_input_state(assignment: str = "", assignment_path: str = "") -> dict[str, str]:
    state = {
        "user_goal": "Подготовить черновик решения перед ручной проверкой.",
    }
    if assignment_path:
        state["assignment_path"] = assignment_path
    else:
        state["assignment"] = assignment
    return state


def save_homework_result(result: dict[str, Any], human_decision: str = "approve") -> Path:
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
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


def run_assignment_agent(
    *,
    assignment: str = "",
    assignment_path: str = "",
    human_decision: str = "approve",
) -> tuple[dict[str, Any], Path]:
    graph = build_graph()
    result = graph.invoke(build_input_state(assignment=assignment, assignment_path=assignment_path))
    output_path = save_homework_result(result, human_decision=human_decision)
    return result, output_path
