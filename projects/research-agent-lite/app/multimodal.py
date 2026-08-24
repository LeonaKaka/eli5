from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class MediaType(StrEnum):
    IMAGE = "image"
    PDF = "pdf"
    AUDIO = "audio"


class AssetRef(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    media_type: MediaType
    mime_type: str = Field(min_length=1)
    size_bytes: int = Field(gt=0)


class SourceRef(BaseModel):
    asset_id: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    timestamp_ms: int | None = Field(default=None, ge=0)
    region: tuple[int, int, int, int] | None = None

    @model_validator(mode="after")
    def validate_region(self) -> "SourceRef":
        if self.region is not None:
            x1, y1, x2, y2 = self.region
            if x2 <= x1 or y2 <= y1:
                raise ValueError("region must have positive width and height")
        return self


class PreparedPart(BaseModel):
    kind: str = Field(pattern="^(text|image|audio)$")
    content: str
    source: SourceRef


class PreparedAsset(BaseModel):
    asset_id: str
    parts: list[PreparedPart]


@dataclass(frozen=True)
class AssetPolicy:
    max_size_bytes: int = 50_000_000
    allowed_media: frozenset[MediaType] = frozenset(
        {MediaType.IMAGE, MediaType.PDF, MediaType.AUDIO}
    )


class AssetPipeline:
    """Provider-neutral metadata/preparation boundary.

    This course project intentionally does not parse real user files yet. It
    models the policy and provenance boundary so later provider/file adapters
    can plug in without letting arbitrary paths flow through the application.
    """

    def __init__(self, policy: AssetPolicy | None = None) -> None:
        self.policy = policy or AssetPolicy()

    def prepare(
        self,
        asset: AssetRef,
        *,
        task: str,
        pages: list[int] | None = None,
    ) -> PreparedAsset:
        self._validate_asset(asset)

        if asset.media_type is MediaType.IMAGE:
            parts = [
                PreparedPart(
                    kind="image",
                    content=f"asset://{asset.id}/original",
                    source=SourceRef(asset_id=asset.id),
                )
            ]
        elif asset.media_type is MediaType.PDF:
            chosen_pages = pages or [1]
            parts = [
                PreparedPart(
                    kind="text",
                    content=f"Extract relevant PDF content for task: {task}",
                    source=SourceRef(asset_id=asset.id, page=page),
                )
                for page in chosen_pages
            ]
        else:
            parts = [
                PreparedPart(
                    kind="audio",
                    content=f"asset://{asset.id}/segment/0",
                    source=SourceRef(asset_id=asset.id, timestamp_ms=0),
                )
            ]

        return PreparedAsset(asset_id=asset.id, parts=parts)

    def _validate_asset(self, asset: AssetRef) -> None:
        if asset.media_type not in self.policy.allowed_media:
            raise ValueError(f"media type not allowed: {asset.media_type}")
        if asset.size_bytes > self.policy.max_size_bytes:
            raise ValueError("asset exceeds size policy")
