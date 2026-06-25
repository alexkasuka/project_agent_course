from src.course_agent import build_graph


def test_graph_runs_end_to_end(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    monkeypatch.setattr("src.course_agent.tools.KNOWLEDGE_PATH", tmp_path / "missing.json")
    graph = build_graph()

    result = graph.invoke(
        {
            "assignment": "Собрать LangGraph агента: описать State, node, tool и human handoff.",
            "user_goal": "draft",
        }
    )

    assert result["draft_solution"]
    assert result["review_request"]
    assert result["retrieved_context"]
    assert result["citations"]
    assert result["retrieval_route"] == "retrieve_context"
    assert result["context_route"] == "draft_solution"
    assert "human_review_required" in result["risk_flags"]


def test_graph_routes_missing_course_context_to_clarification(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    monkeypatch.setattr("src.course_agent.tools.KNOWLEDGE_PATH", tmp_path / "missing.json")
    graph = build_graph()

    result = graph.invoke(
        {
            "assignment": "курс zzzzz unknown topic",
            "user_goal": "draft",
        }
    )

    assert result["retrieved_context"] == []
    assert result["retrieval_route"] == "retrieve_context"
    assert result["context_route"] == "request_clarification"
    assert "no_context_found" in result["risk_flags"]
    assert "clarification_required" in result["risk_flags"]
    assert result["review_request"]


def test_graph_can_skip_retrieval_for_generic_assignment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    monkeypatch.setattr("src.course_agent.tools.KNOWLEDGE_PATH", tmp_path / "missing.json")
    graph = build_graph()

    result = graph.invoke(
        {
            "assignment": "Написать короткий план работы на неделю",
            "user_goal": "draft",
        }
    )

    assert result["assignment_type"] == "generic"
    assert result["retrieval_route"] == "skip_retrieval"
    assert result["context_route"] == "draft_solution"
    assert result["retrieved_context"] == []
    assert "retrieval_skipped" in result["risk_flags"]
    assert result["draft_solution"]


def test_graph_loads_assignment_from_ipynb(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    monkeypatch.setattr("src.course_agent.tools.KNOWLEDGE_PATH", tmp_path / "missing.json")
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
