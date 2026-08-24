from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator

from .multimodal import AssetRef, SourceRef


class BlockType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE_CAPTION = "figure_caption"
    FORMULA = "formula"


class DocumentBlock(BaseModel):
    id: str = Field(min_length=1)
    kind: BlockType
    text: str = Field(min_length=1)
    source: SourceRef
    ordinal: int = Field(ge=0)
    heading_level: int | None = Field(default=None, ge=1, le=6)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_heading(self) -> "DocumentBlock":
        if self.kind is BlockType.HEADING and self.heading_level is None:
            raise ValueError("heading blocks require heading_level")
        if self.kind is not BlockType.HEADING and self.heading_level is not None:
            raise ValueError("heading_level is only valid for heading blocks")
        return self


class Document(BaseModel):
    id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    blocks: list[DocumentBlock]
    parser_version: str = Field(default="v1", min_length=1)

    @model_validator(mode="after")
    def validate_blocks(self) -> "Document":
        ids = [block.id for block in self.blocks]
        if len(ids) != len(set(ids)):
            raise ValueError("document block ids must be unique")
        ordinals = [block.ordinal for block in self.blocks]
        if ordinals != sorted(ordinals):
            raise ValueError("document blocks must already be in reading order")
        if any(block.source.asset_id != self.asset_id for block in self.blocks):
            raise ValueError("all block provenance must point to document asset")
        return self


class DocumentParser(Protocol):
    """Boundary for asset-specific parsers.

    Real PDF/HTML/OCR adapters can implement this protocol later. Keeping the
    parser boundary separate lets retrieval tests operate on a stable Document
    model instead of depending on one parser library's output shape.
    """

    def parse(self, asset: AssetRef) -> Document: ...
