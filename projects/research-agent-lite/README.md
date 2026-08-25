# Research Assistant v6.3

This is the runnable project that grows across the ELI5 AI Agent Engineering course.

Python closed at **v1.0**, LLM Application Engineering at **v2.0**, RAG at **v3.0**, Agent Engineering at **v4.0**, LangChain / LangGraph at **v5.0**, FastAPI closed the backend architecture at **v6.0**, and the compressed Advanced Agent Engineering line now extends the same system.

## Advanced increments

- **v6.1–v6.2 / A1 MCP** — capability interoperability: Host/Client/Server, Tool/Resource/Prompt control ownership, real Python SDK v2 `MCPServer` + `Client` discovery/call/read/get. A1 stops here; MCP protocol minutiae are lookup material rather than ten more lessons.
- **v6.3 / A2 Tool Runtime** — run-scoped workspace, browser adapter, constrained shell runner, separate Python interpreter process and artifact registry. The full teaching flow is browser → saved source → generated Python → artifact.

## Run teaching profile

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
uvicorn app.fastapi_app:app --reload
```

Optional real-browser support:

```bash
pip install -e ".[browser]"
playwright install chromium
```

The tests do not require a network or browser binary; they use `FixtureBrowser` while exercising the same `BrowserAdapter` boundary.

## A2 runtime architecture

```text
Agent / LangGraph
    │ proposes calls
    ▼
AgentToolRuntime
├── BrowserAdapter
├── AgentWorkspace
├── ShellRunner
├── PythonRunner
└── ArtifactRegistry
    │
    ▼
run-scoped files / processes / deliverables
```

A deterministic end-to-end demo is available as `run_research_artifact_demo()`:

```text
Browser.read(url)
→ inputs/source.json
→ work/summarize_source.py
→ separate Python interpreter
→ artifacts/summary.json
```

## What the runtime guardrails do

`AgentWorkspace` rejects absolute paths and parent-directory escape, and only writes under explicit run roots such as `inputs/`, `work/` and `artifacts/`.

`ShellRunner` accepts argv rather than a shell command string, uses `shell=False`, a command allowlist, workspace cwd, a minimal environment, path checks, bounded output and a timeout.

`PythonRunner` writes generated code into the run workspace and executes it with a separate interpreter using `python -I`, workspace cwd, a minimal environment, bounded output and a timeout.

`BrowserPolicy` can restrict schemes and hosts before page content enters the Agent. `PlaywrightBrowser` is the optional real-browser adapter; browser process pooling/lifecycle would belong to a production worker resource manager.

## What these guardrails do NOT do

This project deliberately does **not** call the Python subprocess a security sandbox. A process running as the same OS user can still potentially access host files, network and process capabilities outside the helper API.

Application guardrails:

```text
workspace path checks
cwd
argv + shell=False
command allowlist
sanitized env
timeout
output bounds
browser host allowlist
```

are useful, but a true untrusted-code boundary still needs stronger filesystem mounts, network egress controls, process/capability restrictions, CPU/RAM/time limits and usually container/VM/OS isolation. A3 attacks the current v6.3 runtime directly.

## Current structure

```text
app/
├── tool_runtime.py               # A2 browser/filesystem/shell/python/artifacts
├── mcp_contracts.py              # A1 primitive/control ownership policy
├── mcp_research_server.py        # A1 MCPServer + research capabilities
├── fastapi_app.py                # HTTP product API / health / SSE / commands
├── fastapi_service.py            # v6 composition root / deployment audit
├── fastapi_security.py           # Bearer / Principal / permissions
├── fastapi_errors.py             # ProblemDetails / request correlation
├── fastapi_worker.py             # separate Worker adapter
├── langgraph_production.py       # control-plane ↔ LangGraph bridge
└── production.py                 # tenant RunStore / Queue / optimistic revisions

tests/
├── test_tool_runtime.py
├── test_mcp_primitives.py
├── test_fastapi_lifecycle_production.py
└── ...
```

## Existing ownership boundaries remain intact

- FastAPI owns HTTP/auth/contracts, not long Agent execution.
- RunStore/Queue/Worker own product execution control, not LangGraph checkpoint meaning.
- LangGraph owns graph state/interrupt/resume, not tenant authorization.
- MCP standardizes capability interoperability, not capability permission.
- Tool Runtime owns run-scoped execution mechanics, not model policy or security guarantees.
- Artifact files stay outside model context unless explicitly summarized/read back in.

## Next step

**A3 — Agent Security / Prompt Injection.** Feed untrusted browser/RAG/file content into the v6.3 runtime and test secret access, path escape, network exfiltration, dangerous tool use and confused-deputy behavior. Add trust labels/capability scopes and approval boundaries instead of relying on the model to “ignore malicious instructions.”
