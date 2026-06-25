from src.course_agent.runner import run_assignment_agent, summarize_run


def test_run_assignment_agent_writes_to_custom_output_dir(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    monkeypatch.setattr("src.course_agent.tools.KNOWLEDGE_PATH", tmp_path / "missing.json")

    result, output_path = run_assignment_agent(
        assignment="Собрать LangGraph-агента для учебных заданий",
        output_dir=tmp_path,
    )

    assert output_path.parent == tmp_path
    assert output_path.exists()
    assert "Homework Result" in output_path.read_text(encoding="utf-8")
    assert result["draft_solution"]


def test_summarize_run_returns_machine_readable_fields(tmp_path) -> None:
    output_path = tmp_path / "homework.md"
    result = {
        "model_used": "fallback:test",
        "risk_flags": ["human_review_required"],
        "citations": ["demo.md:c1"],
        "draft_solution": "draft",
        "review_request": "review",
    }

    summary = summarize_run(result, output_path)

    assert summary["output_path"] == str(output_path)
    assert summary["model_used"] == "fallback:test"
    assert summary["risk_flags"] == ["human_review_required"]
    assert summary["citations_count"] == 1
    assert summary["has_draft"] is True
    assert summary["has_human_review"] is True
