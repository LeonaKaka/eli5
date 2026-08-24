# MCP / Tool Ecosystem Roadmap

Scope: evolve Research Assistant v6.0 from application-local tools into a protocol-driven capability ecosystem. MCP standardizes how a host discovers and invokes remote/local capabilities; it does **not** replace application authorization, sandboxing, durable execution, LangGraph state, or business policy.

Current reference line: MCP specification **2026-07-28**, MCP Python SDK **2.x**.

Current progress: **02 / 10 live**, Research Assistant **v6.2**.

## 01 — MCP Mental Model / Host / Client / Server / Primitives ✅
Start from the integration problem: application-local LangChain tools do not scale into a heterogeneous ecosystem of search, files, databases, GitHub, instruments and remote services. Learn the Host → MCP Client → MCP Server boundary and the three core server primitives: tools, resources and prompts. Keep their control models distinct: tools are generally model-controlled actions, resources are application-selected context, prompts are user-selected reusable workflows. Map existing Research Assistant capabilities onto MCP without pretending MCP itself is an Agent runtime.

## 02 — Build a Real MCP Server + Client ✅
Use the current Python SDK v2 `MCPServer` and first-class `Client`. Expose a provider-free Research Assistant capability server with a paper-search tool, concrete/template resources and a comparison prompt. Discover capabilities in-process, inspect generated tool schemas, call a tool, read a resource and render a prompt. Testing uses `Client(server)` so protocol behavior is exercised without a subprocess or port.

## 03 — Transports / stdio / Streamable HTTP / Stateless MCP
Understand transport as deployment topology rather than business semantics. Compare in-process testing, stdio subprocess servers and Streamable HTTP remote servers. Learn the 2026-07-28 stateless request model, `server/discover`, required routing headers, backward compatibility and why legacy HTTP+SSE should not be chosen for new servers.

## 04 — Tool Contracts / Structured Results / Errors / Progress
Design model-facing tools instead of merely decorating functions. Cover generated JSON Schema, descriptions, bounded arguments, structured vs text results, model-visible tool failures vs protocol failures, progress, timeouts and retry policy. Reconnect these rules to approval, idempotency and side-effect safety from Agent Engineering.

## 05 — Resources / Templates / Caching / Change Subscriptions
Use URI-addressed resources for application-controlled context. Cover concrete resources vs RFC 6570 templates, MIME types, JSON/binary content, cache hints, safe namespace design, list/read caching and modern `subscriptions/listen` change events. Decide when context should be a Resource rather than a Tool.

## 06 — Prompts / Completions / User-Controlled Workflows
Treat prompts as reusable user-selected message templates, not hidden system instructions. Cover prompt arguments, generated messages, completions, discoverability/versioning and the boundary between an MCP prompt and the host application's higher-priority policy/instructions.

## 07 — Multi-Server Host / Discovery / Namespacing / Routing
Connect one host to several servers. Handle duplicate tool names, server identity, capability inventory, allowlists, routing, connection lifecycle, degraded servers and per-server budgets. Build a capability registry that can expose a safe subset to a model instead of flattening every connected server into one giant tool list.

## 08 — Authorization / OAuth / Trust / Enterprise MCP Security
Study remote MCP as a security boundary. Cover OAuth-oriented authorization, issuer validation, client metadata, least privilege, credential audience/scope, consent, secret handling and enterprise-managed authorization. Distinguish connection authorization from per-tool business authorization and prepare for the later Agent Security track.

## 09 — MCP ↔ LangGraph / Dynamic Tools / Gateway / Observability
Bridge MCP-discovered capabilities into the existing LangGraph runtime. Keep tool provenance/server identity, permission metadata, tracing and errors visible. Explore MCP gateways/proxies, W3C trace context, tool inventory refresh and why dynamic discovery still needs an application policy layer before the model sees capabilities.

## 10 — Production MCP Ecosystem / Tasks / Extensions / Architecture
Close the MCP line with a production capability architecture: multiple remote servers, stateless HTTP scaling, cache/change semantics, long-running Tasks extension, multi-round-trip user input and deployment boundaries. Define which responsibilities belong to MCP, the Agent host, the sandbox/runtime and infrastructure before moving to Browser/Code/Sandbox Agent engineering.

## Project evolution
Continue `projects/research-agent-lite/` from Research Assistant v6.0:
- v6.1 — MCP primitive/control model and exposure policy ✅
- v6.2 — real MCPServer + in-process Client discovery/calls ✅
- v6.3 — stdio / Streamable HTTP transport boundary
- v6.4 — production-quality MCP tool contracts
- v6.5 — resources/templates/cache/subscriptions
- v6.6 — prompts/completions
- v6.7 — multi-server capability registry/routing
- v6.8 — authorization/trust boundary
- v6.9 — LangGraph/MCP gateway/observability integration
- v7.0 — production MCP ecosystem architecture

## Teaching rule
MCP is an interoperability protocol, not magic Agent intelligence. A server advertising a tool does not make that tool safe to expose; a successful MCP connection does not authorize every action; a resource is not automatically trusted context; and transport durability does not replace RunStore/Queue/checkpoint semantics.