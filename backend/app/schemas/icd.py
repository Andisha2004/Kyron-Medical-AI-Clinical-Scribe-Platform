from pydantic import BaseModel, Field


class IcdSearchResultResponse(BaseModel):
    code: str
    description: str
    category: str | None
    score: float


class IcdSearchQueryParams(BaseModel):
    q: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=20)
