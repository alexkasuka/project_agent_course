from src.course_agent.runner import run_assignment_agent, summarize_run


def test_langfuse_ingestion_batch_is_created_when_tracing_is_enabled(
    monkeypatch,
    tmp_path,
) -> None:
    sent_batches = []

    def fake_send(events):
        sent_batches.append(events)
        return {"sent": True, "status": 207, "response": {"successes": [], "errors": []}}

    monkeypatch.delenv("DISABLE_LANGFUSE", raising=False)
    monkeypatch.setenv("DISABLE_MODEL_CALLS", "1")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setattr("src.course_agent.tracing._send_ingestion_batch", fake_send)

    result, output_path = run_assignment_agent(
        assignment="Собрать LangGraph-агента для учебных заданий",
        output_dir=tmp_path,
    )
    summary = summarize_run(result, output_path)

    assert summary["langfuse_trace_id"]
    assert len(sent_batches) == 1
    events = sent_batches[0]
    assert events[0]["type"] == "trace-create"
    assert any(event["body"]["name"] == "node.retrieve_context" for event in events)
    assert any(event["body"]["name"] == "node.human_review" for event in events)
