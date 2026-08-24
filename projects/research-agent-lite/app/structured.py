from pydantic import BaseModel, Field, model_validator


class PaperAssessment(BaseModel):
    title: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    tags: list[str]
    summary: str = Field(min_length=1)


class StructuredResult(BaseModel):
    assessment: PaperAssessment | None = None
    refusal: str | None = None
    completed: bool = True

    @model_validator(mode="after")
    def check_terminal_shape(self) -> "StructuredResult":
        if self.assessment is None and not self.refusal:
            raise ValueError("result needs either assessment or refusal")
        if self.assessment is not None and self.refusal:
            raise ValueError("assessment and refusal are mutually exclusive")
        return self


def validate_assessment(payload: object) -> PaperAssessment:
    """Final application-side validation boundary for model-produced data."""
    return PaperAssessment.model_validate(payload)
