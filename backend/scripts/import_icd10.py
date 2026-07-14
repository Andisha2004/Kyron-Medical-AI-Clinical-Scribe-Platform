from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.models.icd10_code import Icd10Code
from app.db.session import AsyncSessionLocal
from scripts.seed_demo import icd_seed_entries


async def import_icd10_codes() -> None:
    entries = icd_seed_entries()
    deduplicated_entries: dict[str, dict[str, str | None]] = {}
    for entry in entries:
        deduplicated_entries[str(entry["code"])] = entry

    async with AsyncSessionLocal() as session:
        existing_codes = {
            code.code: code
            for code in (await session.scalars(select(Icd10Code))).all()
        }

        created_count = 0
        updated_count = 0

        for code, entry in deduplicated_entries.items():
            existing = existing_codes.get(code)
            if existing is None:
                session.add(
                    Icd10Code(
                        code=code,
                        description=str(entry["description"]),
                        category=str(entry["category"]) if entry["category"] is not None else None,
                        search_text=str(entry["search_text"]),
                    )
                )
                created_count += 1
                continue

            existing.description = str(entry["description"])
            existing.category = str(entry["category"]) if entry["category"] is not None else None
            existing.search_text = str(entry["search_text"])
            updated_count += 1

        await session.commit()

    print(
        f"ICD-10 import complete. Total unique entries: {len(deduplicated_entries)}. "
        f"Created: {created_count}. Updated: {updated_count}."
    )


if __name__ == "__main__":
    asyncio.run(import_icd10_codes())
