from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.db import models  # noqa: F401
from app.db.base import Base


async def bootstrap() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(bootstrap())
