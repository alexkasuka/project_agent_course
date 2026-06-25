from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .state import AgentState
from .tools import draft_solution_with_model, read_assignment_file, search_knowledge_base
from .tracing import trace_node


def load_assignment(state: AgentState) -> AgentState:
    assignment = state.get("assignment", "").strip()
    assignment_path = state.get("assignment_path", "").strip()

    if assignment or not assignment_path:
        return state

    loaded = read_assignment_file.invoke({"path": assignment_path})
    return {
        **state,
        "assignment": loaded["assignment"],
        "assignment_source": loaded["assignment_source"],
    }


def classify_assignment(state: AgentState) -> AgentState:
    assignment = state.get("assignment", "").lower()
    knowledge_markers = (
        "курс",
        "материал",
        "лекц",
        "langgraph",
        "rag",
        "агент",
        "state",
        "tool",
        "human",
        "handoff",
        "метрик",
    )
    needs_retrieval = any(marker in assignment for marker in knowledge_markers)

    return {
        **state,
        "assignment_type": "course_grounded" if needs_retrieval else "generic",
        "retrieval_route": "retrieve_context" if needs_retrieval else "skip_retrieval",
    }


def route_by_assignment_type(state: AgentState) -> str:
    return state.get("retrieval_route", "retrieve_context")


def retrieve_context(state: AgentState) -> AgentState:
    assignment = state.get("assignment", "").strip()
    documents = search_knowledge_base.invoke({"query": assignment, "limit": 5})
    flags: list[str] = []

    if not assignment:
        flags.append("empty_assignment")
    if not documents:
        flags.append("no_context_found")
    if documents and max(doc["score"] for doc in documents) < 2:
        flags.append("low_retrieval_confidence")

    return {
        **state,
        "retrieved_context": documents,
        "risk_flags": flags,
    }


def skip_retrieval(state: AgentState) -> AgentState:
    flags = list(state.get("risk_flags", []))
    flags.append("retrieval_skipped")
    return {
        **state,
        "retrieved_context": [],
        "risk_flags": flags,
    }


def assess_context(state: AgentState) -> AgentState:
    flags = list(state.get("risk_flags", []))
    documents = state.get("retrieved_context", [])

    if state.get("assignment_type") == "generic":
        context_route = "draft_solution"
    elif not documents:
        context_route = "request_clarification"
    elif "low_retrieval_confidence" in flags:
        context_route = "request_clarification"
    else:
        context_route = "draft_solution"

    return {
        **state,
        "context_route": context_route,
        "risk_flags": flags,
    }


def route_by_context_quality(state: AgentState) -> str:
    return state.get("context_route", "draft_solution")


def request_clarification(state: AgentState) -> AgentState:
    flags = list(state.get("risk_flags", []))
    if "clarification_required" not in flags:
        flags.append("clarification_required")

    return {
        **state,
        "draft_solution": (
            "Недостаточно релевантного контекста для уверенного решения. "
            "Добавьте материалы курса, уточните формулировку задания или подтвердите, "
            "что можно подготовить общий черновик без источников."
        ),
        "citations": [doc["source"] for doc in state.get("retrieved_context", [])],
        "model_used": "none",
        "risk_flags": flags,
    }


def draft_solution(state: AgentState) -> AgentState:
    assignment = state.get("assignment", "").strip()
    documents = state.get("retrieved_context", [])
    flags = list(state.get("risk_flags", []))

    if not assignment:
        draft = "Задание не передано. Нужно добавить текст задания перед запуском агента."
        model_used = "none"
    elif not documents and state.get("assignment_type") != "generic":
        draft = (
            "Черновик пока нельзя подготовить надежно: по материалам курса не найден "
            "релевантный контекст. Нужно добавить презентации или уточнить формулировку."
        )
        model_used = "none"
    else:
        context_lines = [
            f"[{doc['source']}] {doc['snippet']}" for doc in documents
        ]
        result = draft_solution_with_model.invoke(
            {
                "assignment": assignment,
                "context": "\n\n".join(context_lines),
            }
        )
        draft = result["text"]
        model_used = result["model_used"]

    citations = [doc["source"] for doc in documents]

    return {
        **state,
        "draft_solution": draft,
        "citations": citations,
        "risk_flags": flags,
        "model_used": model_used,
    }


def human_review(state: AgentState) -> AgentState:
    flags = list(state.get("risk_flags", []))
    flags.append("human_review_required")

    checklist = [
        "Проверить, что черновик отвечает именно на задание.",
        "Сверить факты с указанными источниками из материалов курса.",
        "Дополнить места, где контекст не найден или уверенность низкая.",
        "Одобрить финальную версию перед отправкой.",
    ]

    return {
        **state,
        "review_request": "Human-in-the-loop review:\n" + "\n".join(f"- {item}" for item in checklist),
        "risk_flags": flags,
    }


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_assignment", trace_node("load_assignment", load_assignment))
    graph.add_node("classify_assignment", trace_node("classify_assignment", classify_assignment))
    graph.add_node("retrieve_context", trace_node("retrieve_context", retrieve_context))
    graph.add_node("skip_retrieval", trace_node("skip_retrieval", skip_retrieval))
    graph.add_node("assess_context", trace_node("assess_context", assess_context))
    graph.add_node("request_clarification", trace_node("request_clarification", request_clarification))
    graph.add_node("draft_solution", trace_node("draft_solution", draft_solution))
    graph.add_node("human_review", trace_node("human_review", human_review))

    graph.add_edge(START, "load_assignment")
    graph.add_edge("load_assignment", "classify_assignment")
    graph.add_conditional_edges(
        "classify_assignment",
        route_by_assignment_type,
        {
            "retrieve_context": "retrieve_context",
            "skip_retrieval": "skip_retrieval",
        },
    )
    graph.add_edge("retrieve_context", "assess_context")
    graph.add_edge("skip_retrieval", "assess_context")
    graph.add_conditional_edges(
        "assess_context",
        route_by_context_quality,
        {
            "draft_solution": "draft_solution",
            "request_clarification": "request_clarification",
        },
    )
    graph.add_edge("draft_solution", "human_review")
    graph.add_edge("request_clarification", "human_review")
    graph.add_edge("human_review", END)

    return graph.compile()
