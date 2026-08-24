# Research Assistant · evolving project

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

The eight Python lessons closed at **Research Agent Lite v1.0**. The LLM Application Engineering track upgrades the same codebase toward **Research Assistant v2.0** instead of starting a new demo.

Current project level: **v1.6**.

## What Python v1.0 demonstrates

- Pydantic request/response models
- modules and package boundaries
- async concurrent I/O-style work
- transient vs permanent failures
- bounded retry and partial results
- dataclass state
- composition / dependency injection
- pytest unit and integration-style tests

## LLM track increments already landed

- **v1.1** — model API / provider boundary concepts
- **v1.2** — conversation state and history strategy
- **v1.3** — `ContextBuilder`, token-budget-aware selection, injectable token estimator
- **v1.4** — semantic `GenerationProfile` objects for extract / research / brainstorm tasks
- **v1.5** — `StreamState`, `StreamResult`, `StreamCollector`; partial output is kept but only `COMPLETED` is final
- **v1.6** — `PaperAssessment` / `StructuredResult`; application-side Pydantic validation and explicit refusal state

The project remains offline-first for now: no API key is required. Real provider adapters arrive later so architecture and failure behavior can be tested before credentials and network variability are introduced.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

python -m app.main "RAG evaluation"
pytest -q
```

## Structure

```text
app/
├── models.py       # validated boundary models
├── state.py        # internal AgentState dataclass
├── errors.py       # error taxonomy
├── sources.py      # PaperSource protocol + demo adapters
├── agent.py        # orchestration, concurrency, retry, partial result
├── context.py      # v1.3 context selection + token budgeting
├── generation.py   # v1.4 provider-neutral generation profiles
├── streaming.py    # v1.5 stream state + partial/final semantics
├── structured.py   # v1.6 structured-output contracts
└── main.py         # CLI entrypoint

tests/
├── test_state.py
├── test_agent.py
├── test_context_generation.py
└── test_streaming_structured.py
```

## Why these modules remain provider-neutral

`ContextBuilder` accepts an injected token estimator because exact tokenization depends on the model. `GenerationProfile` stores semantic intent instead of pretending every provider exposes identical knobs. `StreamCollector` models terminal states without copying one provider's event names, and `structured.py` keeps the application's final validation boundary independent of whichever provider produced the payload.

## Next step

LLM 07–08 add a controlled tool-call boundary and multimodal/file inputs. After that, a real provider adapter can map these neutral concepts onto the capabilities actually supported by the chosen model API.
