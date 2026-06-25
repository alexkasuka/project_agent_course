from __future__ import annotations

from typing import TypedDict


class RetrievedDocument(TypedDict):
    source: str
    title: str
    snippet: str
    score: int


class AgentState(TypedDict, total=False):
    assignment: str
    assignment_path: str
    assignment_source: str
    user_goal: str
    assignment_type: str
    retrieval_route: str
    context_route: str
    retrieved_context: list[RetrievedDocument]
    risk_flags: list[str]
    draft_solution: str
    review_request: str
    citations: list[str]
    model_used: str
