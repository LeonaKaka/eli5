# Advanced A1 — MCP / External Capability Ecosystem

MCP is now one high-density advanced chapter rather than a ten-lesson subtrack.

Status: **A1 complete**, Research Assistant **v6.2**.

## Part 1 — Mental model ✅
Host → MCP Client → MCP Server. Separate Tools / Resources / Prompts by control ownership and keep MCP distinct from Agent state, authorization, approval and durable execution.

## Part 2 — Real server + client ✅
Use current Python SDK v2 `MCPServer` and first-class `Client`. The Research Assistant exposes a paper-search Tool, concrete/template Resources and a comparison Prompt; tests discover and exercise them through the MCP client surface.

## What is intentionally not expanded into standalone lessons

Transport details, stdio vs Streamable HTTP mechanics, progress notifications, protocol-field evolution, prompt completions, subscriptions, OAuth field-by-field details, Tasks/extensions and gateway implementation are important reference material but do not each change enough engineering judgment to justify separate course chapters.

When later chapters need remote MCP, authorization or tracing, those details will be introduced in context.

## Boundary to carry forward

- MCP discovery does not grant tool permission.
- Resource content is not automatically trusted.
- MCP does not replace LangGraph state/checkpoints.
- MCP transport does not replace RunStore/Queue durability.
- Tool schemas do not replace application authorization, approval or side-effect idempotency.

Next: **A2 Browser / Shell / Python / Filesystem Runtime** in `docs/advanced-agent-roadmap.md`.
