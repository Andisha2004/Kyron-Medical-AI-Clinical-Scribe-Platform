from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
