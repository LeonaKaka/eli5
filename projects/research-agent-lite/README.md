# Research Assistant · evolving project

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

The eight Python lessons closed at **Research Agent Lite v1.0**. The LLM Application Engineering track now upgrades the same codebase toward **Research Assistant v2.0** instead of starting a new demo.

Current project level: **v1.4**.

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

The project remains offline-first for now: no API key is required. Real provider adapters arrive later in the LLM track so the architecture can be learned and tested before credentials and network variability are introduced.

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
└── main.py         # CLI entrypoint

tests/
├── test_state.py
├── test_agent.py
└── test_context_generation.py
```

## Why the new modules are provider-neutral

`ContextBuilder` accepts an injected token estimator because exact tokenization depends on the target model. `GenerationProfile` stores semantic intent (`low/high reasoning`, `low/high randomness`) rather than pretending every provider exposes identical parameter names.

## Next step

LLM 05–06 will add streaming and structured outputs. After that, a real provider adapter can map these provider-neutral concepts onto the model capabilities actually supported by that provider.
