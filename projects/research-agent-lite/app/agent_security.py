from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class ContentTrust(StrEnum):
    TRUSTED_APP = "trusted_app"
    USER_PROVIDED = "user_provided"
    EXTERNAL_UNTRUSTED = "external_untrusted"


@dataclass(frozen=True)
class ContextChunk:
    """One piece of model-visible context with immutable provenance/trust metadata.

    The label is a policy signal, not a sanitizer. Marking browser/RAG/file text as
    untrusted does not make the language model ignore instructions inside it; it
    lets application code prevent that text from silently expanding authority.
    """

    source: str
    text: str
    trust: ContentTrust


class Capability(StrEnum):
    READ_WORKSPACE = "read_workspace"
    WRITE_WORKSPACE = "write_workspace"
    RUN_PYTHON = "run_python"
    RUN_SHELL = "run_shell"
    NETWORK_FETCH = "network_fetch"
    NETWORK_SEND = "network_send"
    READ_SECRET = "read_secret"


class SecurityDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    APPROVAL_REQUIRED = "approval_required"


@dataclass(frozen=True)
class RunAuthority:
    """Authority granted by authenticated product policy, not by prompt text."""

    allowed_capabilities: frozenset[Capability]
    allowed_egress_hosts: frozenset[str] = frozenset()
    tainted_requires_approval: frozenset[Capability] = frozenset(
        {
            Capability.RUN_PYTHON,
            Capability.RUN_SHELL,
            Capability.NETWORK_SEND,
        }
    )


@dataclass(frozen=True)
class ToolIntent:
    capability: Capability
    target: str
    arguments: dict[str, object]
    context: tuple[ContextChunk, ...] = ()

    def fingerprint(self) -> str:
        canonical = json.dumps(
            {
                "capability": self.capability.value,
                "target": self.target,
                "arguments": self.arguments,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def contains_untrusted_external_content(self) -> bool:
        return any(chunk.trust is ContentTrust.EXTERNAL_UNTRUSTED for chunk in self.context)


@dataclass(frozen=True)
class ApprovalGrant:
    """Approval is bound to one exact intent fingerprint, never a generic unlock."""

    intent_fingerprint: str
    actor_id: str
    approved: bool = True


@dataclass(frozen=True)
class PolicyResult:
    decision: SecurityDecision
    reason: str
    intent_fingerprint: str


class AgentSecurityPolicy:
    """Host-side policy for model-proposed real-world actions.

    Key design rule: content can influence the model, but content cannot grant
    capability. Authority comes from authenticated application state. Untrusted
    context therefore changes the required controls for sensitive actions rather
    than being trusted to police itself through prompt wording.
    """

    def evaluate(
        self,
        intent: ToolIntent,
        *,
        authority: RunAuthority,
        approval: ApprovalGrant | None = None,
    ) -> PolicyResult:
        fingerprint = intent.fingerprint()

        if intent.capability is Capability.READ_SECRET:
            return PolicyResult(
                SecurityDecision.DENY,
                "raw secrets are host-only and are never exposed as a model-readable capability",
                fingerprint,
            )

        if intent.capability not in authority.allowed_capabilities:
            return PolicyResult(
                SecurityDecision.DENY,
                f"run authority does not grant capability: {intent.capability.value}",
                fingerprint,
            )

        if intent.capability in {Capability.NETWORK_FETCH, Capability.NETWORK_SEND}:
            parsed = urlparse(intent.target)
            host = parsed.hostname or ""
            if parsed.scheme not in {"http", "https"} or not host:
                return PolicyResult(
                    SecurityDecision.DENY,
                    "network target must be an absolute http(s) URL",
                    fingerprint,
                )
            if host not in authority.allowed_egress_hosts:
                return PolicyResult(
                    SecurityDecision.DENY,
                    f"network host is outside the run egress allowlist: {host}",
                    fingerprint,
                )

        sensitive_tainted_action = (
            intent.contains_untrusted_external_content
            and intent.capability in authority.tainted_requires_approval
        )
        if sensitive_tainted_action:
            if approval is None:
                return PolicyResult(
                    SecurityDecision.APPROVAL_REQUIRED,
                    "sensitive action was proposed from external untrusted context",
                    fingerprint,
                )
            if not approval.approved:
                return PolicyResult(
                    SecurityDecision.DENY,
                    "human approval rejected this exact action",
                    fingerprint,
                )
            if approval.intent_fingerprint != fingerprint:
                return PolicyResult(
                    SecurityDecision.DENY,
                    "approval is bound to a different action fingerprint",
                    fingerprint,
                )

        return PolicyResult(SecurityDecision.ALLOW, "host policy allows this exact action", fingerprint)


def external_context(*, source: str, text: str) -> ContextChunk:
    """Mark browser/RAG/file/tool-output text as untrusted external data."""

    return ContextChunk(source=source, text=text, trust=ContentTrust.EXTERNAL_UNTRUSTED)


def trusted_app_context(*, source: str, text: str) -> ContextChunk:
    return ContextChunk(source=source, text=text, trust=ContentTrust.TRUSTED_APP)


def injection_signal(text: str) -> bool:
    """Tiny teaching heuristic used only for telemetry/adversarial demos.

    A detector may raise suspicion, but its output must never be treated as the
    authorization boundary. Prompt injection can be paraphrased or obfuscated.
    """

    lowered = " ".join(text.lower().split())
    markers = (
        "ignore previous",
        "ignore all previous",
        "system prompt",
        "read the secret",
        "upload the secret",
        "exfiltrate",
    )
    return any(marker in lowered for marker in markers)
