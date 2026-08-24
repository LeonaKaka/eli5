# Research Assistant v2.0

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

The eight Python lessons closed at **Research Agent Lite v1.0**. The ten LLM Application Engineering lessons then upgraded the same codebase into **Research Assistant v2.0** instead of starting a new demo.

Current project level: **v2.0**.

## What Python v1.0 demonstrates

- Pydantic request/response models
- modules and package boundaries
- async concurrent I/O-style work
- transient vs permanent failures
- bounded retry and partial results
- dataclass state
- composition / dependency injection
- pytest unit and integration-style tests

## LLM increments

- **v1.1** — model API / provider boundary concepts
- **v1.2** — conversation state and history strategy
- **v1.3** — `ContextBuilder`, token-budget-aware selection, injectable token estimator
- **v1.4** — semantic `GenerationProfile` objects for task-specific generation/reasoning intent
- **v1.5** — `StreamState`, `StreamResult`, `StreamCollector`; partial output is not automatically final
- **v1.6** — `PaperAssessment` / `StructuredResult`; Pydantic validation and explicit refusal state
- **v1.7** — `ToolCall`, `ToolRegistry`, `ToolExecutor`; arguments are validated and side effects require explicit approval
- **v1.8** — `AssetRef`, `SourceRef`, `PreparedAsset`, `AssetPipeline`; file policy and page/timestamp provenance are explicit
- **v1.9** — `ModelRouter`; capability gates happen before weighted quality/cost/latency/reliability ranking
- **v2.0** — `EvalCase`, `EvalReport`, `RegressionGate`; critical-slice regressions can block release even when the average improves

The project remains offline-first: no API key is required. The goal is to make architecture, contracts and failure behavior deterministic before mapping them onto a real provider SDK.

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
├── context.py      # context selection + token budgeting
├── generation.py   # provider-neutral generation profiles
├── streaming.py    # stream state + partial/final semantics
├── structured.py   # structured-output contracts
├── tools.py        # tool schema / permission / execution boundary
├── multimodal.py   # asset policy, preparation and provenance
├── routing.py      # capability gate + explainable model routing
├── evals.py        # eval reports + regression gate
└── main.py         # CLI entrypoint

tests/
├── test_state.py
├── test_agent.py
├── test_context_generation.py
├── test_streaming_structured.py
├── test_tools_multimodal.py
└── test_routing_evals.py
```

## Why these modules remain provider-neutral

The project teaches durable engineering boundaries rather than one SDK's current parameter names. A later real provider adapter can map tokenization, reasoning controls, stream events, tool schemas, file inputs and usage accounting onto the chosen provider while keeping the application contracts testable.

## Next step

The next course track is RAG. It can reuse `AssetRef`, `SourceRef`, `ContextBuilder`, structured outputs, routing and evals while adding parsing, chunking, embeddings, retrieval, hybrid search, reranking and citation-quality evaluation.
