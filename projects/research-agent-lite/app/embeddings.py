from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field, model_validator

from .chunking import Chunk

Vector = list[float]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    _check_same_dimension(a, b)
    return sum(x * y for x, y in zip(a, b, strict=True))


def l2_distance(a: Sequence[float], b: Sequence[float]) -> float:
    _check_same_dimension(a, b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    _check_same_dimension(a, b)
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        raise ValueError("cosine similarity is undefined for a zero vector")
    return dot(a, b) / (na * nb)


def normalize(vector: Sequence[float]) -> Vector:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return [0.0 for _ in vector]
    return [x / norm for x in vector]


def _check_same_dimension(a: Sequence[float], b: Sequence[float]) -> None:
    if len(a) != len(b):
        raise ValueError(f"vector dimension mismatch: {len(a)} != {len(b)}")


class EmbeddingProvider(Protocol):
    model_id: str
    dimension: int
    normalized: bool

    def embed(self, texts: list[str]) -> list[Vector]: ...


class EmbeddingRecord(BaseModel):
    chunk_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    dimension: int = Field(gt=0)
    normalized: bool
    vector: Vector

    @model_validator(mode="after")
    def validate_dimension(self) -> "EmbeddingRecord":
        if len(self.vector) != self.dimension:
            raise ValueError("vector length does not match embedding dimension")
        return self


class EmbeddingService:
    """Turn retrieval chunks into versioned embedding records.

    The service deliberately records model id, dimension and normalization so
    an index cannot silently mix incompatible vector spaces.
    """

    def __init__(self, provider: EmbeddingProvider) -> None:
        self.provider = provider

    def embed_chunks(self, chunks: list[Chunk]) -> list[EmbeddingRecord]:
        vectors = self.provider.embed([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("embedding provider returned the wrong number of vectors")

        records: list[EmbeddingRecord] = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            if len(vector) != self.provider.dimension:
                raise ValueError("embedding provider returned an unexpected dimension")
            records.append(
                EmbeddingRecord(
                    chunk_id=chunk.id,
                    model_id=self.provider.model_id,
                    dimension=self.provider.dimension,
                    normalized=self.provider.normalized,
                    vector=vector,
                )
            )
        return records


class DeterministicToyEmbeddingProvider:
    """Offline teaching adapter, not a semantic embedding model.

    Tokens are hashed into signed vector buckets. It exists only so tests can
    exercise batching, dimensions, normalization and vector-index contracts
    without network access or an API key.
    """

    model_id = "toy-hash-embedding-v1"
    normalized = True

    def __init__(self, dimension: int = 16) -> None:
        if dimension < 2:
            raise ValueError("dimension must be >= 2")
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[Vector]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> Vector:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[\w-]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        return normalize(vector)
