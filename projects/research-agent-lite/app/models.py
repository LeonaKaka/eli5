from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class Paper(BaseModel):
    title: str
    source: str
    score: float = Field(ge=0.0, le=1.0)


class AgentAnswer(BaseModel):
    question: str
    papers: list[Paper]
    warnings: list[str] = Field(default_factory=list)
