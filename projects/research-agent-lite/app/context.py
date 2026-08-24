from collections.abc import Callable
from dataclasses import dataclass

TokenEstimator = Callable[[str], int]


def rough_token_estimate(text: str) -> int:
    """Cheap preflight estimate only; production code should use model-aware counting or provider usage."""
    return max(1, len(text) // 3)


@dataclass(frozen=True)
class ContextBlock:
    kind: str
    content: str
    priority: int
    estimated_tokens: int


class ContextBuilder:
    """Build a relevance-first context without letting history grow forever."""

    def __init__(self, estimator: TokenEstimator = rough_token_estimate) -> None:
        self.estimator = estimator

    def build(
        self,
        *,
        instructions: str,
        history: list[dict[str, str]],
        evidence: list[str],
        input_budget: int,
    ) -> list[ContextBlock]:
        if input_budget < 1:
            raise ValueError("input_budget must be >= 1")

        candidates: list[ContextBlock] = []
        candidates.append(self._block("instructions", instructions, priority=100))

        for item in evidence:
            candidates.append(self._block("evidence", item, priority=90))

        # Recent history is normally more useful than very old conversational detail.
        for age, message in enumerate(reversed(history)):
            priority = max(20, 70 - age)
            candidates.append(
                self._block(
                    f"history:{message.get('role', 'unknown')}",
                    message.get("content", ""),
                    priority=priority,
                )
            )

        selected: list[ContextBlock] = []
        used = 0
        for block in sorted(candidates, key=lambda b: b.priority, reverse=True):
            if used + block.estimated_tokens > input_budget:
                continue
            selected.append(block)
            used += block.estimated_tokens

        # Put the selected blocks back into a useful reading order.
        order = {"instructions": 0, "evidence": 1}
        selected.sort(key=lambda b: order.get(b.kind.split(":", 1)[0], 2))
        return selected

    def _block(self, kind: str, content: str, *, priority: int) -> ContextBlock:
        return ContextBlock(
            kind=kind,
            content=content,
            priority=priority,
            estimated_tokens=self.estimator(content),
        )
