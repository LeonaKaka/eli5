# ELI5 — AI Agent Engineering

Public static learning site for AI Agent engineering, built as an interactive ELI5 course rather than a glossary.

## Current tracks

### Python — 8/8 complete
- 01 Data, references, branching, loops, functions · Research Agent v0.1
- 02 Function contracts, type hints, Pydantic, schemas · v0.2
- 03 Modules, packages, imports, dependency direction, project structure · v0.3
- 04 HTTP, JSON, status codes, httpx, API clients · v0.4
- 05 async / await, event loop, gather, concurrency limits · v0.5
- 06 exceptions, retry/backoff, logging, fallback, idempotency · v0.6
- 07 class, dataclass, mutable defaults, composition, AgentState · v0.7
- 08 pytest, mock/fake, test layers, runnable Research Agent Lite · v1.0

### LLM Application Engineering — 2/10 live
- 01 Model API / Request Lifecycle ✅
- 02 Messages / Instructions / Conversation State ✅
- 03 Tokens / Context Window / Context Engineering / Caching
- 04 Generation & Reasoning Controls
- 05 Streaming
- 06 Structured Outputs
- 07 Tool / Function Calling
- 08 Multimodal / Files
- 09 Model Selection / Cost / Latency / Reliability
- 10 Evals / Prompt Lifecycle / Production Safety

Full scope: `docs/llm-app-roadmap.md`.

## Teaching contract
Every lesson must include:
1. A concrete engineering problem first
2. A visual/explorable explanation
3. Code evolution rather than only final code
4. At least one failure/bug example
5. A continuous project increment
6. Exercises + interview-level checks

## Runnable Python project

`projects/research-agent-lite/` is the Python course-closing project. It runs without an API key and includes Pydantic models, async source adapters, bounded retry, partial results, dataclass state, composition, pytest tests, and CI.

```bash
cd projects/research-agent-lite
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m app.main "RAG evaluation" --top-k 3
pytest -q
```

Local verification during development: `4 passed`, and the CLI exercised one transient retry successfully.

## Project evolution

Python closes at `Research Agent Lite v1.0`. The LLM track upgrades that same project into `Research Assistant v2.0` with a provider-abstracted model client, conversation/context management, streaming, structured outputs, one controlled tool call, model routing, usage accounting, and an eval suite.

## Pages
Deployed with GitHub Actions from the repository root. No build step, backend, or secret is required for the learning UI.
