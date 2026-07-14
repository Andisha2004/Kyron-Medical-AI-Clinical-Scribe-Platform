from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    environment: str
    database_status: str | None = None
    database_pool: dict[str, int | bool] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
