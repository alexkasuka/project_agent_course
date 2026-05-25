from src.course_agent import build_graph


def test_graph_runs_end_to_end(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    graph = build_graph()

    result = graph.invoke(
        {
            "assignment": "Собрать LangGraph-агента для выполнения заданий с human-in-the-loop.",
            "user_goal": "draft",
        }
    )

    assert result["draft_solution"]
    assert result["review_request"]
    assert result["retrieved_context"]
    assert result["citations"]
    assert "human_review_required" in result["risk_flags"]


def test_graph_handles_missing_context(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    graph = build_graph()

    result = graph.invoke(
        {
            "assignment": "zzzzzz unknown topic",
            "user_goal": "draft",
        }
    )

    assert result["retrieved_context"] == []
    assert "no_context_found" in result["risk_flags"]
    assert result["review_request"]


def test_graph_loads_assignment_from_ipynb(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    notebook_path = tmp_path / "assignment.ipynb"
    notebook_path.write_text(
        """
{
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {},
      "source": ["# Задание\\n", "Соберите LangGraph workflow с State и human-in-the-loop."]
    },
    {
      "cell_type": "code",
      "metadata": {},
      "source": ["graph = build_graph()\\n", "graph.invoke(input_data)"]
    }
  ],
  "metadata": {},
  "nbformat": 4,
  "nbformat_minor": 5
}
""".strip(),
        encoding="utf-8",
    )
    graph = build_graph()

    result = graph.invoke(
        {
            "assignment_path": str(notebook_path),
            "user_goal": "draft",
        }
    )

    assert "LangGraph workflow" in result["assignment"]
    assert result["assignment_source"] == str(notebook_path)
    assert result["draft_solution"]
