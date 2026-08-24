# Research Agent Lite v1.0

This is the runnable project produced by the eight Python lessons in the ELI5 AI Agent Engineering course.

It is intentionally small and offline-first: the default paper sources are local demo adapters, so you can run the full architecture without an API key. In the next course stage, those adapters can be replaced with real LLM/search clients.

## What it demonstrates

- Pydantic request/response models
- modules and package boundaries
- async concurrent I/O-style work
- transient vs permanent failures
- bounded retry and partial results
- dataclass state
- composition / dependency injection
- pytest unit and integration-style tests

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
├── models.py    # validated boundary models
├── state.py     # internal AgentState dataclass
├── errors.py    # error taxonomy
├── sources.py   # PaperSource protocol + demo adapters
├── agent.py     # orchestration, concurrency, retry, partial result
└── main.py      # CLI entrypoint

tests/
├── test_state.py
└── test_agent.py
```

## Next step

Replace `DemoPaperSource` with real adapters while keeping the same `PaperSource` interface. The rest of the agent should not need to know whether a source is local, HTTP-based, or LLM-backed.
