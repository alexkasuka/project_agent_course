# PRD: Diploma Assignment Assistant

## 1. Summary

Проект дорабатывается из учебного помощника для выполнения заданий в дипломный AI-agent кейс: агент на LangGraph принимает учебное задание, читает материалы курса, выбирает подходящий сценарий обработки, готовит решение, проверяет качество, отправляет результат на human review и сохраняет итоговый артефакт.

Цель PRD — зафиксировать, что именно нужно добавить, исправить и протестировать, чтобы проект соответствовал требованиям дипломного проекта курса N1.

## 2. Product Goal

Создать работающего AI-агента для реальной задачи студента: быстро получить проверяемый черновик решения учебного задания на основе материалов курса.

Агент должен демонстрировать инженерный подход:

- явная архитектура LangGraph;
- нелинейный workflow с ветвлениями;
- RAG по материалам курса;
- минимум три tool;
- benchmark и eval-кейсы;
- LangFuse tracing;
- security checklist;
- CLI-интерфейс для демонстрации;
- README с метриками и объяснением архитектурных решений.

## 3. Current State

Уже реализовано:

- CLI-запуск: `run_assignment_agent.py`;
- LangGraph graph: `src/course_agent/graph.py`;
- State: `src/course_agent/state.py`;
- загрузка заданий из текста, `.pdf`, `.ipynb`, `.md`;
- загрузка материалов курса из `.pdf`, `.ipynb`, `.md`;
- JSON knowledge base: `data/course_knowledge.json`;
- keyword search tool;
- генерация через OpenRouter, Ollama или fallback;
- human review step;
- сохранение результата в `outputs/homework_result_*.md`;
- CLI параметры `--output-dir`, `--json`, `--verbose`;
- две точки ветвления в LangGraph:
  - `route_by_assignment_type`;
  - `route_by_context_quality`;
- benchmark skeleton на 10 кейсов: `benchmarks/assignment_cases.json`;
- benchmark runner: `scripts/run_benchmark.py`;
- smoke-тесты.

Основные ограничения текущей версии:

- ветвления добавлены, но их нужно усилить более точной классификацией и validation route;
- RAG реализован простым keyword search без оценки retrieval quality;
- tool-вызовы есть, но не все явно валидируются тестами;
- benchmark из 10 запросов добавлен, но его нужно расширить отчетом и включить в README как регулярную метрику;
- нет LangFuse tracing;
- нет LLM-as-judge eval;
- нет security checklist в README;
- нет latency/cost/success-rate метрик;
- README пока описывает учебный MVP, а не дипломный engineering case.

## 4. Users

Primary user: студент курса, который хочет получить черновик решения задания по материалам курса.

Secondary users:

- ментор курса, который проверяет архитектуру и качество проекта;
- рекрутер или заказчик, который смотрит проект как портфельный кейс.

## 5. Target User Flow

```text
1. User puts course materials into course_materials/
2. User runs scripts/ingest_course_materials.py
3. User passes assignment text or file to run_assignment_agent.py
4. Agent loads assignment
5. Agent classifies assignment complexity and required mode
6. Agent retrieves course context when needed
7. Agent drafts solution
8. Agent evaluates solution quality
9. Agent routes result:
   - enough context and valid draft -> human_review
   - no context / low confidence -> clarification or fallback path
   - failed validation -> revise_draft
10. Agent saves final Markdown artifact
11. LangFuse stores trace of run, nodes, tool calls, timing and model usage
```

## 6. Functional Requirements

### FR1. LangGraph Agent With Branching

Current graph:

```text
load_assignment -> retrieve_context -> draft_solution -> human_review
```

Target graph:

```text
load_assignment
  -> classify_assignment
  -> route_by_assignment_type
       -> retrieve_context
       -> skip_retrieval
  -> assess_context
  -> route_by_context_quality
       -> draft_solution
       -> request_clarification
  -> validate_draft
  -> route_by_validation
       -> human_review
       -> revise_draft
  -> save_result
```

Minimum two branching points:

1. `route_by_assignment_type`
   - if assignment needs course knowledge -> `retrieve_context`
   - if assignment is generic/project-management only -> `skip_retrieval`

2. `route_by_context_quality`
   - if context found and confidence enough -> `draft_solution`
   - if no context or low confidence -> `request_clarification`

Optional third branching:

3. `route_by_validation`
   - if draft passes checks -> `human_review`
   - if draft fails -> `revise_draft`

Files to change:

- `src/course_agent/state.py`
- `src/course_agent/graph.py`
- `tests/test_graph.py`

Acceptance criteria:

- graph compiles;
- graph has at least two `add_conditional_edges`;
- tests cover each route;
- README explains why LangGraph is useful for this task.

### FR2. RAG Over Course Materials

Keep JSON/keyword search for the MVP, but make RAG explicit and measurable.

Required behavior:

- ingest `.pdf`, `.ipynb`, `.md`;
- store chunks in `data/course_knowledge.json`;
- retrieve top-K chunks;
- return citations in final output;
- mark `no_context_found` and `low_retrieval_confidence` in state.

Optional improvement:

- add lightweight embeddings later if benchmark shows retrieval quality is weak.

Files to change:

- `src/course_agent/tools.py`
- `src/course_agent/document_loader.py`
- `scripts/ingest_course_materials.py`
- `README.md`

Acceptance criteria:

- one test checks retrieval returns relevant demo materials;
- one benchmark metric tracks retrieval success.

### FR3. Minimum Three Tools

Current useful tools:

- `read_assignment_file`;
- `search_knowledge_base`;
- `draft_solution_with_model`.

Add or formalize:

- `save_result_file` as a tool or keep it in runner but explain as filesystem action;
- `evaluate_draft_quality` for deterministic checks;
- `trace_event` or LangFuse integration wrapper.

Required minimum for diploma:

1. `read_assignment_file` — filesystem tool.
2. `search_knowledge_base` — local RAG/search tool.
3. `draft_solution_with_model` — external model API / local model tool.

At least one external interaction:

- OpenRouter API call, or
- filesystem read/write, or
- LangFuse tracing.

Acceptance criteria:

- tests verify at least one expected tool call path;
- README lists all tools and external systems.

### FR4. Benchmark

Create benchmark dataset with at least 10 cases.

Target file:

- `benchmarks/assignment_cases.json`

Schema:

```json
[
  {
    "id": "case_001",
    "input": "Create a LangGraph assignment assistant",
    "expected_output": {
      "must_include": ["State", "tool", "human review"],
      "must_have_citations": true,
      "expected_route": "human_review"
    }
  }
]
```

Benchmark runner:

- `scripts/run_benchmark.py`

Metrics:

- success rate;
- retrieval hit rate;
- average latency;
- p95 latency;
- model_used distribution;
- number of failed / fallback runs.

Acceptance criteria:

- at least 10 benchmark cases;
- benchmark produces JSON or Markdown report;
- README includes latest success rate.

### FR5. Eval Cases

Need at least three types of checks:

1. Programmatic assert
   - example: output has `draft_solution`, `review_request`, `citations`.

2. LLM-as-judge
   - judge prompt checks whether answer covers assignment and is grounded in context.
   - can use OpenRouter model.

3. Tool-call correctness
   - verify assignment file loading tool is used for `assignment_path`;
   - verify retrieval tool returns citations;
   - verify missing context route sets `no_context_found`.

Target files:

- `tests/test_graph.py`
- `tests/test_tools.py`
- `evals/llm_judge.py`
- `scripts/run_evals.py`

Acceptance criteria:

- tests run locally;
- LLM judge can be skipped without API key;
- CI/local command documented in README.

### FR6. LangFuse Observability

Add tracing for real runs.

Required data in trace:

- run id;
- assignment source;
- selected route;
- retrieved source count;
- tool names;
- model used;
- latency per node;
- final risk flags.

Target implementation options:

- direct LangFuse SDK wrapper;
- callback/instrumentation around node functions;
- environment controlled by `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`.

Target files:

- `src/course_agent/observability.py`
- updates in `src/course_agent/graph.py` or `runner.py`
- `.env.example`
- README section.

Acceptance criteria:

- when LangFuse env vars exist, runs create traces;
- when env vars are absent, agent still runs without failure;
- README includes screenshot/link placeholder or instructions for showing trace.

### FR7. Security Checklist

Add security checklist to README.

Required statuses:

- implemented;
- not applicable;
- open.

Checklist topics:

- API keys excluded from Git;
- `.env.example` only contains placeholders;
- private course files ignored;
- generated outputs ignored;
- input file type allowlist;
- max file size limit;
- prompt injection risk in course materials;
- tool allowlist;
- external HTTP domain allowlist;
- PII handling;
- human approval before final submission;
- logging does not expose secrets.

Acceptance criteria:

- README has table with status and notes;
- at least basic input format allowlist exists in code.

### FR8. README Upgrade

README must include:

- problem statement;
- target user;
- architecture;
- graph diagram;
- tools;
- RAG explanation;
- benchmark metrics:
  - success rate;
  - p95 latency;
  - cost per run;
- security checklist;
- setup and demo instructions;
- explanation of why this is an agent and not just a pipeline.

Acceptance criteria:

- mentor can understand project in under 5 minutes;
- README includes copy-paste commands;
- README includes output artifact example.

### FR9. Demo Interface

Current CLI is acceptable, but it should look like product entrypoint.

Keep:

- `run_assignment_agent.py`

Add:

- `--show-steps` or `--verbose`;
- `--output-dir`;
- `--json` optional machine-readable output.

Optional:

- simple FastAPI endpoint;
- simple Streamlit UI.

Acceptance criteria:

- user can run one command and get a saved result;
- README has CLI examples;
- CLI exits non-zero on invalid input.

## 7. Non-Functional Requirements

### Reliability

- Agent must not crash when OpenRouter or Ollama is unavailable.
- Missing course index should fall back to demo knowledge base.
- Unsupported assignment file type should return clear error.

### Performance

Initial targets:

- p95 latency without model calls: < 2 seconds.
- p95 latency with OpenRouter: < 60 seconds.
- benchmark suite without LLM judge: < 30 seconds.

### Cost

Track:

- model used;
- number of model calls;
- estimated cost per run if provider returns usage.

Initial target:

- fallback/offline mode cost: $0.
- OpenRouter free mode: $0 when free model is available.

### Maintainability

- Keep business logic in `src/course_agent/`.
- Keep CLI thin.
- Tests should not require network by default.

## 8. Architecture Decision

This project should remain an agent rather than a pure pipeline because:

- the workflow must branch based on context quality;
- the system may decide whether retrieval is needed;
- validation can route to revision or human review;
- future versions can choose different model/tool paths.

If a future version removes branching and decisions, README must explain why deterministic pipeline is sufficient.

## 9. Proposed Implementation Plan

### Stage 1. Productize Current Agent

Scope:

- add `docs/PRD.md`;
- add README link to PRD;
- add CLI `--verbose`, `--output-dir`, `--json`;
- add security checklist.

Tests:

- CLI invalid input;
- output file creation;
- no API key fallback.

### How To Update This PRD From New Course Materials

When new course materials appear:

1. Put files into `course_materials/`.
2. Run:

```bash
python scripts/ingest_course_materials.py
```

3. Ask the agent or manually inspect the new materials for:
   - new required capabilities;
   - new security requirements;
   - new observability/evaluation practices;
   - new architecture recommendations;
   - examples that should become benchmark cases.

4. Update this PRD in these sections:
   - `Functional Requirements` for product changes;
   - `Benchmark Draft Cases` for new checks;
   - `Security Checklist` requirements in README;
   - `Implementation Plan` for new stages;
   - `Open Questions` for unresolved architectural choices.

5. Convert each accepted PRD change into:
   - code task;
   - test task;
   - demo/README task;
   - acceptance criteria.

This keeps the PRD as the source of truth for future agent iterations, not a one-time document.

### Stage 2. Add Branching Graph

Scope:

- add `classify_assignment`;
- add `assess_context`;
- add `validate_draft`;
- add conditional edges.

Tests:

- route to retrieval;
- route to skip retrieval;
- route to clarification;
- route to human review.

### Stage 3. Benchmark And Metrics

Scope:

- add `benchmarks/assignment_cases.json`;
- add `scripts/run_benchmark.py`;
- output benchmark report.

Tests:

- benchmark loads 10 cases;
- success rate computed;
- p95 latency computed.

### Stage 4. Eval Suite

Scope:

- programmatic asserts;
- tool-call correctness tests;
- LLM-as-judge optional runner.

Tests:

- eval runner works without API key by skipping LLM judge;
- eval runner works with API key.

### Stage 5. LangFuse

Scope:

- add `observability.py`;
- add trace spans around nodes/tools;
- update `.env.example`;
- document how to inspect traces.

Tests:

- no LangFuse env -> no crash;
- mocked LangFuse client receives event.

### Stage 6. README And Demo Polish

Scope:

- graph diagram;
- metrics table;
- security checklist;
- demo command;
- sample output excerpt.

Tests:

- all documented commands run locally.

## 10. Benchmark Draft Cases

Initial 10 cases:

1. Create a LangGraph assignment assistant.
2. Create a RAG system with retrieval metrics.
3. Explain when human-in-the-loop is needed.
4. Load an assignment from an `.ipynb` file.
5. Handle an assignment with no relevant course context.
6. Ask for a generic plan that does not require retrieval.
7. Generate a solution with required citations.
8. Evaluate answer quality and list missing parts.
9. Save final output as Markdown.
10. Detect unsupported file type and return clear error.

## 11. Success Metrics

Minimum diploma targets:

- benchmark size: >= 10 cases;
- success rate: >= 80% on deterministic/fallback mode;
- smoke tests: pass;
- eval types: 3/3 implemented;
- LangFuse traces: at least 3 real runs;
- p95 latency documented;
- cost per run documented;
- security checklist present.

## 12. Open Questions

- Should the final project include a small web UI, or is CLI enough?
- Should retrieval remain keyword-based or move to embeddings before final submission?
- Which OpenRouter model should be preferred for LLM-as-judge?
- Should human review be simulated in CLI or stored as a separate approval file?
- Should benchmark expected outputs be strict strings or rubric-based assertions?

## 13. Definition Of Done

Project is ready for diploma review when:

- README has architecture, graph, metrics, benchmark results and security checklist;
- LangGraph has at least two conditional branches;
- at least three tools are documented and tested;
- RAG path is implemented and justified;
- 10-case benchmark exists and can be run;
- eval suite includes programmatic assert, LLM-as-judge and tool correctness;
- LangFuse traces are available for real runs;
- CLI demo works from a fresh clone using demo materials;
- generated outputs and secrets are excluded from GitHub.
