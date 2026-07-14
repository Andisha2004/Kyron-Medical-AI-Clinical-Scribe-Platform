import asyncio
from pathlib import Path
import sys

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import engine


async def main() -> None:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT current_database(), current_user"))
        database_name, current_user = result.one()
        print(f"database={database_name}")
        print(f"user={current_user}")


if __name__ == "__main__":
    asyncio.run(main())
