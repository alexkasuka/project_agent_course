import pytest


@pytest.fixture(autouse=True)
def disable_external_tracing(monkeypatch) -> None:
    monkeypatch.setenv("DISABLE_LANGFUSE", "1")
