from dataclasses import dataclass
from typing import Literal

Level = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class GenerationProfile:
    """Provider-neutral intent; adapters may map these fields differently per model."""

    name: str
    randomness: Level
    reasoning: Level
    max_output_tokens: int

    def __post_init__(self) -> None:
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be >= 1")


EXTRACT = GenerationProfile(
    name="extract",
    randomness="low",
    reasoning="low",
    max_output_tokens=1200,
)

RESEARCH = GenerationProfile(
    name="research",
    randomness="low",
    reasoning="high",
    max_output_tokens=4200,
)

BRAINSTORM = GenerationProfile(
    name="brainstorm",
    randomness="high",
    reasoning="medium",
    max_output_tokens=1800,
)
