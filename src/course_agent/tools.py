from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from .document_loader import extract_document_plain_text

TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9_]+", re.UNICODE)
KNOWLEDGE_PATH = Path("data/course_knowledge.json")

KNOWLEDGE_BASE = [
    {
        "source": "course:langgraph",
        "title": "LangGraph basics",
        "text": (
            "LangGraph помогает описывать агентные приложения как граф состояний: "
            "State хранит данные между шагами, node выполняет логику, edge задает маршрут."
        ),
    },
    {
        "source": "course:rag",
        "title": "RAG quality checklist",
        "text": (
            "RAG-агент должен отделять найденный контекст от генерации ответа, "
            "возвращать источники и честно сообщать, если данных недостаточно."
        ),
    },
    {
        "source": "ops:handoff",
        "title": "Human handoff",
        "text": (
            "Если запрос требует доступа к закрытым системам, персональным данным или "
            "уверенность низкая, агент должен передать задачу человеку."
        ),
    },
]


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def _load_knowledge_base() -> list[dict[str, Any]]:
    if not KNOWLEDGE_PATH.exists():
        return KNOWLEDGE_BASE

    records = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        return KNOWLEDGE_BASE
    return records


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


@tool
def search_knowledge_base(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Search a small course knowledge base and return ranked text snippets."""
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    ranked: list[dict[str, Any]] = []
    for item in _load_knowledge_base():
        item_text = item.get("text") or item.get("snippet") or ""
        text = f"{item.get('title', '')} {item_text}"
        score = len(query_tokens & _tokens(text))
        if score == 0:
            continue
        ranked.append(
            {
                "source": item["source"],
                "title": item.get("title", item["source"]),
                "snippet": item_text,
                "score": score,
            }
        )

    ranked.sort(key=lambda row: row["score"], reverse=True)
    return ranked[:limit]


@tool
def read_assignment_file(path: str) -> dict[str, str]:
    """Read assignment text from a PDF or Jupyter/Colab notebook file."""
    document_path = Path(path).expanduser()
    text = extract_document_plain_text(document_path)
    return {
        "assignment": text,
        "assignment_source": str(document_path),
    }


def _fallback_draft(assignment: str = "", context: str = "") -> dict[str, str]:
    context_note = "Контекст найден и использован." if context.strip() else "Контекст не найден."
    return {
        "text": (
            "# Решение задания\n\n"
            "## Понимание задачи\n\n"
            f"{assignment.strip() or 'Задание не передано.'}\n\n"
            "Нужно собрать минимальный LangGraph-агент, который принимает учебное задание, "
            "ищет релевантные материалы курса, готовит черновик решения и передает его "
            "человеку на проверку перед финальной сдачей.\n\n"
            "## Использованные материалы\n\n"
            f"{context_note} Ключевые элементы из материалов: State хранит данные графа, "
            "node возвращает обновления состояния, tool выполняет детерминированную работу, "
            "human-in-the-loop нужен для проверки и утверждения результата.\n\n"
            "## Минимальная реализация\n\n"
            "```python\n"
            "from typing import TypedDict\n"
            "from langgraph.graph import START, END, StateGraph\n\n"
            "class AgentState(TypedDict, total=False):\n"
            "    assignment: str\n"
            "    retrieved_context: list[dict]\n"
            "    draft_solution: str\n"
            "    review_request: str\n"
            "    citations: list[str]\n"
            "    risk_flags: list[str]\n\n"
            "def retrieve_context(state: AgentState) -> AgentState:\n"
            "    # Здесь вызывается tool поиска по материалам курса.\n"
            "    docs = search_knowledge_base.invoke({\"query\": state[\"assignment\"], \"limit\": 5})\n"
            "    return {**state, \"retrieved_context\": docs, \"citations\": [d[\"source\"] for d in docs]}\n\n"
            "def draft_solution(state: AgentState) -> AgentState:\n"
            "    # Здесь вызывается OpenRouter/Ollama/fallback model tool.\n"
            "    draft = draft_solution_with_model.invoke({\n"
            "        \"assignment\": state[\"assignment\"],\n"
            "        \"context\": \"\\n\".join(d[\"snippet\"] for d in state.get(\"retrieved_context\", [])),\n"
            "    })\n"
            "    return {**state, \"draft_solution\": draft[\"text\"]}\n\n"
            "def human_review(state: AgentState) -> AgentState:\n"
            "    return {\n"
            "        **state,\n"
            "        \"review_request\": \"Проверить черновик, источники и соответствие заданию.\",\n"
            "        \"risk_flags\": [*state.get(\"risk_flags\", []), \"human_review_required\"],\n"
            "    }\n\n"
            "builder = StateGraph(AgentState)\n"
            "builder.add_node(\"retrieve_context\", retrieve_context)\n"
            "builder.add_node(\"draft_solution\", draft_solution)\n"
            "builder.add_node(\"human_review\", human_review)\n"
            "builder.add_edge(START, \"retrieve_context\")\n"
            "builder.add_edge(\"retrieve_context\", \"draft_solution\")\n"
            "builder.add_edge(\"draft_solution\", \"human_review\")\n"
            "builder.add_edge(\"human_review\", END)\n"
            "graph = builder.compile()\n"
            "```\n\n"
            "## Что считается выполненным\n\n"
            "- Есть описанный `AgentState`.\n"
            "- Есть минимум два узла с реальной логикой: поиск контекста и подготовка решения.\n"
            "- Есть tool для поиска по материалам курса.\n"
            "- Есть handoff: результат не считается финальным до проверки человеком.\n"
            "- Результат сохраняется в Markdown-файл в папке `outputs/`.\n\n"
            "## Что проверить человеку\n\n"
            "- Черновик действительно отвечает на формулировку задания.\n"
            "- Источники из материалов курса релевантны.\n"
            "- Кодовый каркас запускается локально.\n"
            "- Нет выдуманных фактов и лишней автоматизации без проверки."
        ),
        "model_used": "fallback:no_model",
    }


def _build_prompt(assignment: str, context: str) -> str:
    return (
        "Ты помощник студента. Подготовь краткий черновик выполнения задания "
        "на основе материалов курса. Обязательно отдели факты из контекста от "
        "предложенной реализации. Не выдумывай факты, которых нет в контексте.\n\n"
        f"Задание:\n{assignment}\n\n"
        f"Материалы курса:\n{context}\n"
    )


def _draft_with_openrouter(prompt: str) -> dict[str, str] | None:
    _load_env_file()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    primary_model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    fallback_models = [
        model.strip()
        for model in os.getenv(
            "OPENROUTER_FALLBACK_MODELS",
            "openrouter/free,poolside/laguna-m.1:free,nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        ).split(",")
        if model.strip()
    ]
    models = list(dict.fromkeys([primary_model, *fallback_models]))
    endpoint = os.getenv("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")

    for model in models:
        payload = json.dumps(
            {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "temperature": 0.1,
            }
        ).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": "Course Assignment Assistant",
        }
        referer = os.getenv("OPENROUTER_HTTP_REFERER")
        if referer:
            headers["HTTP-Referer"] = referer

        request = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = str(data["choices"][0]["message"]["content"]).strip()
            used_model = str(data.get("model") or model)
            if text:
                return {"text": text, "model_used": f"openrouter:{used_model}"}
        except urllib.error.HTTPError as error:
            if error.code in {408, 409, 425, 429, 500, 502, 503, 504}:
                continue
            return None
        except (KeyError, IndexError, TypeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue

    return None


def _draft_with_ollama(prompt: str) -> dict[str, str] | None:
    model = os.getenv("LOCAL_LLM_MODEL", "llama3.2:1b")
    endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/api/generate")
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = str(data.get("response", "")).strip()
        if text:
            return {"text": text, "model_used": f"ollama:{model}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    return None


@tool
def draft_solution_with_model(assignment: str, context: str) -> dict[str, str]:
    """Draft an assignment solution via OpenRouter, Ollama, or a deterministic fallback."""
    prompt = _build_prompt(assignment, context)

    if os.getenv("DISABLE_MODEL_CALLS") == "1" or os.getenv("DISABLE_LOCAL_LLM") == "1":
        fallback = _fallback_draft(assignment, context)
        fallback["model_used"] = "fallback:disabled"
        return fallback

    openrouter_result = _draft_with_openrouter(prompt)
    if openrouter_result is not None:
        return openrouter_result

    ollama_result = _draft_with_ollama(prompt)
    if ollama_result is not None:
        return ollama_result

    return _fallback_draft(assignment, context)


@tool
def draft_with_local_model(assignment: str, context: str) -> dict[str, str]:
    """Backward-compatible wrapper for the old tool name."""
    return draft_solution_with_model.invoke({"assignment": assignment, "context": context})
