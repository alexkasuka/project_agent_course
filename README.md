# Assignment Assistant

Учебный LangGraph-агент для выполнения заданий курса по загруженным материалам.

## Концепция агента

Агент помогает студенту выполнять задания курса на основе загруженных материалов. Пользователь передает текст задания, агент ищет релевантные фрагменты в презентациях, готовит черновик решения и всегда отправляет результат на human-in-the-loop проверку перед финальной сдачей.

Пользователь: студент курса, которому нужно быстро собрать первый черновик задания и не потерять требования из материалов.

Что умеет:

- читает материалы курса из `.pdf`, `.ipynb` и `.md`;
- читает задание из текста, PDF, Markdown или Colab/Jupyter notebook;
- ищет релевантные фрагменты в локальном JSON-индексе;
- готовит черновик решения через OpenRouter, Ollama или fallback;
- всегда отправляет результат на human-in-the-loop проверку;
- сохраняет итоговую домашку в `outputs/`.

Ожидаемые edge cases:

- пустое или слишком общее задание;
- задание пришло PDF, Markdown или Colab/Jupyter notebook файлом;
- релевантный контекст не найден;
- низкая уверенность поиска;
- локальная модель не запущена;
- черновик требует ручной доработки.

Критерии качества:

- граф компилируется и проходит end-to-end на задании;
- State явно хранит задание, найденный контекст, черновик, handoff-запрос, флаги риска и источники;
- tool-поиск вызывается из отдельного узла;
- локальная модель используется через tool, но есть fallback без внешних сервисов;
- каждый результат проходит human-in-the-loop review.

## Структура

- `src/course_agent/` — код агента;
- `docs/PRD.md` — план доработки до дипломного проекта;
- `scripts/ingest_course_materials.py` — индексирует материалы курса;
- `course_materials/` — сюда кладутся PDF, Markdown и notebooks курса;
- `assignments/` — сюда кладутся задания;
- `outputs/` — сюда сохраняются выполненные задания;
- `run_assignment_agent.py` — запуск агента;
- `tests/` — smoke-тесты.

Граф идет по контролируемому workflow с ветвлениями:

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
  -> human_review
```

## Быстрый запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/ingest_course_materials.py
python run_assignment_agent.py --assignment "Создать LangGraph-систему для выполнения учебных заданий"
```

После запуска появится Markdown-файл с результатом в `outputs/`.

## Тестовый сценарий без API-ключей

В репозитории есть синтетические demo-материалы `course_materials/demo_*`, поэтому проект можно проверить без приватных файлов курса и без OpenRouter/Ollama.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/ingest_course_materials.py
DISABLE_MODEL_CALLS=1 python run_assignment_agent.py \
  --assignment "Создать LangGraph-систему для выполнения учебных заданий"
```

Ожидаемый результат:

- в консоли появится путь вида `outputs/homework_result_*.md`;
- `Model used` будет `fallback:disabled`;
- в итоговом Markdown будут `Draft Solution`, `Human Review`, `Sources` и `Run Metadata`.

Smoke-тесты:

```bash
python -m pytest tests/test_graph.py
```

## Как пользоваться

1. Положите материалы курса в `course_materials/`.
2. Соберите индекс:

```bash
python scripts/ingest_course_materials.py
```

3. Положите задание в `assignments/`.
4. Запустите выполнение:

```bash
python run_assignment_agent.py --assignment-path assignments/homework_01.ipynb
```

или передайте задание текстом:

```bash
python run_assignment_agent.py --assignment "Собрать LangGraph-агента с State, tool и human-in-the-loop"
```

Полезные параметры CLI:

```bash
python run_assignment_agent.py \
  --assignment "Собрать LangGraph-агента" \
  --output-dir outputs \
  --json
```

- `--output-dir` — куда сохранить Markdown-результат;
- `--json` — машинно-читаемый summary запуска;
- `--verbose` — вывести источники в консоль;
- `--human-decision approve|changes` — записать решение human review в результат.

5. Посмотрите результат в `outputs/homework_result_*.md`.

Схема пайплайна:

```text
course_materials/*.pdf,*.ipynb,*.md
  -> scripts/ingest_course_materials.py
  -> data/course_knowledge.json

assignment text или assignments/*.pdf,*.ipynb,*.md
  -> load_assignment
  -> classify_assignment
  -> search_knowledge_base
  -> assess_context
  -> draft_solution_with_model
  -> human_review
  -> outputs/homework_result_*.md
```

Если OpenRouter настроен, черновик генерируется моделью. Если модель недоступна, проект всё равно создает структурированное решение через fallback.

Векторная база здесь намеренно не используется: для первого каркаса достаточно JSON-индекса и keyword search. Это проще показать, легче отлаживать и не требует тяжелых локальных зависимостей.

## LangFuse tracing

Агент умеет отправлять traces в LangFuse через `/api/public/ingestion`. Это опционально: без ключей LangFuse проект запускается как раньше.

Чтобы включить tracing:

```bash
cp .env.example .env
# затем впишите LANGFUSE_PUBLIC_KEY и LANGFUSE_SECRET_KEY
python run_assignment_agent.py --assignment "Создать LangGraph-систему для выполнения учебных заданий"
```

Что попадает в LangFuse:

- один root trace `assignment-agent-run` на каждый запуск;
- observation span `langgraph.invoke`;
- отдельные observation spans для узлов графа: `load_assignment`, `classify_assignment`, `retrieve_context`, `assess_context`, `draft_solution`, `human_review`;
- metadata по маршрутам, количеству источников, флагам риска, модели и наличию handoff.

Если tracing нужно временно отключить:

```bash
DISABLE_LANGFUSE=1 python run_assignment_agent.py --assignment "Создать учебного агента"
```

## Benchmark

В проекте есть первичный benchmark из 10 кейсов:

```bash
python scripts/ingest_course_materials.py
python scripts/run_benchmark.py
```

По умолчанию benchmark отключает model calls и проверяет deterministic/fallback режим. Для проверки с реальной моделью:

```bash
python scripts/run_benchmark.py --use-model
```

Текущий локальный прогон на полном индексе материалов:

```text
total: 10
passed: 10
success_rate: 1.0
retrieval_hit_rate: 0.7
p95_latency_ms: 1073.39
```

## OpenRouter

Для генерации черновика через OpenRouter добавьте API-ключ:

```bash
cp .env.example .env
# затем впишите свой OPENROUTER_API_KEY в .env
python run_assignment_agent.py --assignment "Создать учебного агента"
```

`OPENROUTER_MODEL` можно не задавать: `openrouter/free` используется по умолчанию. Если выбранная бесплатная модель временно rate-limited, агент попробует запасные модели из `OPENROUTER_FALLBACK_MODELS`, затем Ollama, затем fallback.

Пример фиксированного списка:

```bash
export OPENROUTER_MODEL="qwen/qwen3-coder:free"
export OPENROUTER_FALLBACK_MODELS="openrouter/free,poolside/laguna-m.1:free,nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
```

## Локальная модель

Если OpenRouter не настроен, агент пытается вызвать Ollama:

```bash
ollama pull llama3.2:1b
ollama serve
LOCAL_LLM_MODEL=llama3.2:1b python run_assignment_agent.py --assignment "Создать учебного агента"
```

Если ни OpenRouter, ни Ollama не доступны, агент не падает: `draft_solution_with_model` вернет простой fallback-черновик и пометит `model_used` как `fallback:no_model`.

## Дальнейшие шаги

- улучшить поиск по материалам через embeddings;
- добавить сохранение approved-версии после human review;
- добавить условные переходы для `no_context_found` и `low_retrieval_confidence`;
- покрыть основные сценарии тестами.
