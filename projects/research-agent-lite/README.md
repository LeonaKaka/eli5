# Research Assistant · evolving project

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

The eight Python lessons closed at **Research Agent Lite v1.0**. The LLM Application Engineering track upgrades the same codebase toward **Research Assistant v2.0** instead of starting a new demo.

Current project level: **v1.8**.

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
- **v1.4** — semantic `GenerationProfile` objects for task-specific generation/reasoning intent
- **v1.5** — `StreamState`, `StreamResult`, `StreamCollector`; partial output is not automatically final
- **v1.6** — `PaperAssessment` / `StructuredResult`; Pydantic validation and explicit refusal state
- **v1.7** — `ToolCall`, `ToolRegistry`, `ToolExecutor`; arguments are validated and side effects require explicit approval
- **v1.8** — `AssetRef`, `SourceRef`, `PreparedAsset`, `AssetPipeline`; file policy and page/timestamp provenance are explicit

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
├── tools.py        # v1.7 tool schema / permission / execution boundary
├── multimodal.py   # v1.8 asset policy, preparation and provenance
└── main.py         # CLI entrypoint

tests/
├── test_state.py
├── test_agent.py
├── test_context_generation.py
├── test_streaming_structured.py
└── test_tools_multimodal.py
```

## Why these modules remain provider-neutral

`ContextBuilder` accepts an injected token estimator because exact tokenization depends on the model. `GenerationProfile` stores semantic intent instead of pretending every provider exposes identical knobs. `StreamCollector` models terminal states without copying one provider's event names. `ToolExecutor` treats model tool calls as untrusted proposals until schema and permission checks pass. `AssetPipeline` separates a stored asset from the smaller, provenance-carrying parts actually sent to a model.

## Next step

LLM 09–10 will add model-routing / reliability policy and an eval + prompt-lifecycle layer. After those boundaries are stable, a real provider adapter can map this neutral architecture onto the capabilities actually supported by the chosen model API.
