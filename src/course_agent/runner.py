from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .graph import build_graph
from .tracing import compact_state, flush_traces, trace_span


def build_input_state(assignment: str = "", assignment_path: str = "") -> dict[str, str]:
    state = {
        "user_goal": "Подготовить черновик решения перед ручной проверкой.",
    }
    if assignment_path:
        state["assignment_path"] = assignment_path
    else:
        state["assignment"] = assignment
    return state


def save_homework_result(
    result: dict[str, Any],
    human_decision: str = "approve",
    output_dir: str | Path = "outputs",
) -> Path:
    output_dir = Path(output_dir)
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
    output_dir: str | Path = "outputs",
) -> tuple[dict[str, Any], Path]:
    graph = build_graph()
    input_state = build_input_state(assignment=assignment, assignment_path=assignment_path)

    with trace_span(
        "assignment-agent-run",
        input_data=compact_state(input_state),
        metadata={"human_decision": human_decision},
        tags=["assignment-assistant", "langgraph"],
    ) as root_span:
        with trace_span("langgraph.invoke", input_data=compact_state(input_state)) as invoke_span:
            result = graph.invoke(input_state)
            if invoke_span is not None:
                try:
                    invoke_span.update(output=compact_state(result))
                except Exception:
                    pass

        with trace_span("save_homework_result", input_data=compact_state(result)) as save_span:
            output_path = save_homework_result(result, human_decision=human_decision, output_dir=output_dir)
            if save_span is not None:
                try:
                    save_span.update(output={"output_path": str(output_path)})
                except Exception:
                    pass

        if root_span is not None:
            trace_id = getattr(root_span, "trace_id", "")
            if trace_id:
                result["langfuse_trace_id"] = trace_id
            try:
                root_span.update(output=summarize_run(result, output_path))
            except Exception:
                pass

    flush_traces()
    return result, output_path


def summarize_run(result: dict[str, Any], output_path: Path) -> dict[str, Any]:
    return {
        "output_path": str(output_path),
        "model_used": result.get("model_used", "unknown"),
        "risk_flags": result.get("risk_flags", []),
        "citations_count": len(result.get("citations", [])),
        "has_draft": bool(result.get("draft_solution")),
        "has_human_review": bool(result.get("review_request")),
        "langfuse_trace_id": result.get("langfuse_trace_id", ""),
    }
