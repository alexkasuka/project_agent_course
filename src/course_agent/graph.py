from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .state import AgentState
from .tools import draft_solution_with_model, read_assignment_file, search_knowledge_base


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


def draft_solution(state: AgentState) -> AgentState:
    assignment = state.get("assignment", "").strip()
    documents = state.get("retrieved_context", [])
    flags = list(state.get("risk_flags", []))

    if not assignment:
        draft = "Задание не передано. Нужно добавить текст задания перед запуском агента."
        model_used = "none"
    elif not documents:
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
    graph.add_node("load_assignment", load_assignment)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("draft_solution", draft_solution)
    graph.add_node("human_review", human_review)

    graph.add_edge(START, "load_assignment")
    graph.add_edge("load_assignment", "retrieve_context")
    graph.add_edge("retrieve_context", "draft_solution")
    graph.add_edge("draft_solution", "human_review")
    graph.add_edge("human_review", END)

    return graph.compile()
