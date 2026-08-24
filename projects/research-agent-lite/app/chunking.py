from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from .documents import BlockType, Document, DocumentBlock
from .multimodal import SourceRef


@dataclass(frozen=True)
class ChunkPolicy:
    target_chars: int = 900
    overlap_chars: int = 120
    preserve_tables: bool = True
    include_heading_path: bool = True
    version: str = "v1"

    def __post_init__(self) -> None:
        if self.target_chars < 50:
            raise ValueError("target_chars must be >= 50")
        if self.overlap_chars < 0:
            raise ValueError("overlap_chars must be >= 0")
        if self.overlap_chars >= self.target_chars:
            raise ValueError("overlap_chars must be smaller than target_chars")
        if not self.version:
            raise ValueError("version must not be empty")


class Chunk(BaseModel):
    id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    sources: list[SourceRef]
    heading_path: list[str] = Field(default_factory=list)
    ordinal: int = Field(ge=0)
    policy_version: str = Field(min_length=1)


class StructureAwareChunker:
    """Chunk structured document blocks without reparsing the source asset."""

    def chunk(self, document: Document, *, policy: ChunkPolicy | None = None) -> list[Chunk]:
        policy = policy or ChunkPolicy()
        chunks: list[Chunk] = []
        heading_stack: list[tuple[int, str]] = []
        buffer: list[DocumentBlock] = []

        def current_heading_path() -> list[str]:
            return [text for _, text in heading_stack]

        def flush() -> None:
            nonlocal buffer
            if not buffer:
                return
            text = self._render_buffer(buffer, current_heading_path(), policy)
            chunks.append(
                Chunk(
                    id=f"{document.id}:chunk:{len(chunks)}:{policy.version}",
                    document_id=document.id,
                    text=text,
                    sources=[block.source for block in buffer],
                    heading_path=current_heading_path(),
                    ordinal=len(chunks),
                    policy_version=policy.version,
                )
            )
            if policy.overlap_chars > 0:
                tail = text[-policy.overlap_chars :]
                synthetic = DocumentBlock(
                    id=f"overlap:{len(chunks)}",
                    kind=BlockType.PARAGRAPH,
                    text=tail,
                    source=buffer[-1].source,
                    ordinal=buffer[-1].ordinal,
                )
                buffer = [synthetic]
            else:
                buffer = []

        for block in document.blocks:
            if block.kind is BlockType.HEADING:
                flush()
                level = block.heading_level or 1
                heading_stack = [(l, t) for l, t in heading_stack if l < level]
                heading_stack.append((level, block.text))
                buffer = []
                continue

            if block.kind is BlockType.TABLE and policy.preserve_tables:
                flush()
                table_text = self._render_buffer([block], current_heading_path(), policy)
                chunks.append(
                    Chunk(
                        id=f"{document.id}:chunk:{len(chunks)}:{policy.version}",
                        document_id=document.id,
                        text=table_text,
                        sources=[block.source],
                        heading_path=current_heading_path(),
                        ordinal=len(chunks),
                        policy_version=policy.version,
                    )
                )
                buffer = []
                continue

            candidate = buffer + [block]
            candidate_text = self._render_buffer(candidate, current_heading_path(), policy)
            if buffer and len(candidate_text) > policy.target_chars:
                flush()
            buffer.append(block)

        flush()
        return chunks

    @staticmethod
    def _render_buffer(blocks: list[DocumentBlock], heading_path: list[str], policy: ChunkPolicy) -> str:
        parts: list[str] = []
        if policy.include_heading_path and heading_path:
            parts.append(" > ".join(heading_path))
        parts.extend(block.text for block in blocks)
        return "\n\n".join(part.strip() for part in parts if part.strip())
