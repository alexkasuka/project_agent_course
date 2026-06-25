from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterator

from .state import AgentState

_CURRENT_TRACE_ID: ContextVar[str | None] = ContextVar("course_agent_trace_id", default=None)
_CURRENT_PARENT_ID: ContextVar[str | None] = ContextVar("course_agent_parent_id", default=None)
_CURRENT_EVENTS: ContextVar[list[dict[str, Any]] | None] = ContextVar("course_agent_events", default=None)


def _load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def tracing_enabled() -> bool:
    _load_env_file()
    if os.getenv("DISABLE_LANGFUSE") == "1":
        return False
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id() -> str:
    return uuid.uuid4().hex


def _truncate(value: str, limit: int = 600) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "..."


def compact_state(state: dict[str, Any]) -> dict[str, Any]:
    documents = state.get("retrieved_context", [])
    citations = state.get("citations", [])
    assignment = str(state.get("assignment", ""))

    return {
        "assignment_preview": _truncate(assignment),
        "assignment_path": state.get("assignment_path", ""),
        "assignment_source": state.get("assignment_source", ""),
        "assignment_type": state.get("assignment_type", ""),
        "retrieval_route": state.get("retrieval_route", ""),
        "context_route": state.get("context_route", ""),
        "retrieved_context_count": len(documents) if isinstance(documents, list) else 0,
        "citations_count": len(citations) if isinstance(citations, list) else 0,
        "risk_flags": state.get("risk_flags", []),
        "model_used": state.get("model_used", ""),
        "has_draft_solution": bool(state.get("draft_solution")),
        "has_review_request": bool(state.get("review_request")),
    }


def _base_url() -> str:
    return os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").rstrip("/")


def _send_ingestion_batch(events: list[dict[str, Any]]) -> dict[str, Any]:
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    if not events or not public_key or not secret_key:
        return {"sent": False, "reason": "missing_config"}

    credentials = base64.b64encode(f"{public_key}:{secret_key}".encode("utf-8")).decode("ascii")
    payload = json.dumps({"batch": events}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{_base_url()}/api/public/ingestion",
        data=payload,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    timeout = float(os.getenv("LANGFUSE_TIMEOUT", "5"))

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {
                "sent": True,
                "status": response.status,
                "response": json.loads(body) if body else {},
            }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return {"sent": False, "reason": type(error).__name__}


class HttpTraceSpan:
    def __init__(
        self,
        *,
        name: str,
        input_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        self.name = name
        self.input = input_data
        self.output: Any = None
        self.metadata = metadata or {}
        self.tags = tags or []
        self.id = _new_id()
        self.trace_id = _CURRENT_TRACE_ID.get() or _new_id()
        self.parent_id = _CURRENT_PARENT_ID.get()
        self.start_time = _now_iso()
        self.end_time = self.start_time
        self.is_root = _CURRENT_TRACE_ID.get() is None

    def update(self, **kwargs: Any) -> None:
        if "output" in kwargs:
            self.output = kwargs["output"]
        if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
            self.metadata = {**self.metadata, **kwargs["metadata"]}

    def observation_event(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "id": self.id,
            "traceId": self.trace_id,
            "type": "SPAN",
            "name": self.name,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "input": self.input,
            "output": self.output,
            "metadata": self.metadata,
        }
        if self.parent_id:
            body["parentObservationId"] = self.parent_id

        return {
            "id": _new_id(),
            "timestamp": self.end_time,
            "type": "observation-create",
            "body": body,
        }

    def trace_event(self) -> dict[str, Any]:
        return {
            "id": _new_id(),
            "timestamp": self.end_time,
            "type": "trace-create",
            "body": {
                "id": self.trace_id,
                "timestamp": self.start_time,
                "name": self.name,
                "input": self.input,
                "output": self.output,
                "metadata": self.metadata,
                "tags": self.tags,
                "environment": os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "development"),
            },
        }


@contextmanager
def trace_span(
    name: str,
    *,
    input_data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[HttpTraceSpan | None]:
    if not tracing_enabled():
        yield None
        return

    span = HttpTraceSpan(name=name, input_data=input_data, metadata=metadata, tags=tags)
    trace_token = _CURRENT_TRACE_ID.set(span.trace_id)
    parent_token = _CURRENT_PARENT_ID.set(span.id)
    events_token = None
    if span.is_root:
        events_token = _CURRENT_EVENTS.set([])

    try:
        yield span
    finally:
        span.end_time = _now_iso()
        events = _CURRENT_EVENTS.get()
        if events is not None:
            events.append(span.observation_event())
            if span.is_root:
                _send_ingestion_batch([span.trace_event(), *events])

        _CURRENT_PARENT_ID.reset(parent_token)
        _CURRENT_TRACE_ID.reset(trace_token)
        if events_token is not None:
            _CURRENT_EVENTS.reset(events_token)


def trace_node(name: str, func: Callable[[AgentState], AgentState]) -> Callable[[AgentState], AgentState]:
    @wraps(func)
    def wrapped(state: AgentState) -> AgentState:
        with trace_span(f"node.{name}", input_data=compact_state(dict(state))) as span:
            result = func(state)
            if span is not None:
                span.update(output=compact_state(dict(result)))
            return result

    return wrapped


def flush_traces() -> None:
    return None
