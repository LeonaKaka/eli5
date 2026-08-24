# ELI5 — AI Agent Engineering

Public static learning site for AI Agent engineering, built as an interactive ELI5 course rather than a glossary.

## Live curriculum
- Python 01 — Data, references, branching, loops, functions · Research Agent v0.1
- Python 02 — Function contracts, type hints, Pydantic, schemas · v0.2
- Python 03 — Modules, packages, imports, dependency direction, project structure · v0.3
- Python 04 — HTTP, JSON, status codes, httpx, API clients · v0.4
- Python 05 — async / await, event loop, gather, concurrency limits · v0.5
- Python 06 — exceptions, retry/backoff, logging, fallback, idempotency · v0.6
- Python 07 — class, dataclass, mutable defaults, composition, AgentState · v0.7
- Python 08 — pytest, mock/fake, test layers, runnable Research Agent Lite · v1.0

## Teaching contract
Every lesson must include:
1. A concrete engineering problem first
2. A visual/explorable explanation
3. Code evolution rather than only final code
4. At least one failure/bug example
5. A Research Agent project increment
6. Exercises + interview-level checks

## Python sequence
01. Data building blocks and execution ✅
02. Functions, type hints, Pydantic ✅
03. Modules, packages, project structure ✅
04. HTTP, JSON, APIs ✅
05. async / await ✅
06. Failure engineering ✅
07. Classes, dataclasses, state ✅
08. Testing + Research Agent Lite v1.0 ✅

## Runnable project

`projects/research-agent-lite/` is the course-closing project. It runs without an API key and includes Pydantic models, async source adapters, bounded retry, partial results, dataclass state, composition, pytest tests, and CI.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m app.main "RAG evaluation" --top-k 3
pytest -q
```

Local verification during development: `4 passed`, and the CLI exercised one transient retry successfully.

## Pages
Deployed with GitHub Actions from the repository root. No build step, backend, or secret is required for the learning UI.

## Next stage
LLM Application Engineering: model APIs, messages/context, streaming, structured output, tool calling, cost/latency, and eval-driven iteration.
