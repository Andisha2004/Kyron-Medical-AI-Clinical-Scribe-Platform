import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.icd10_code import Icd10Code


def normalize_search_text(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_code(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def trigram_set(value: str) -> set[str]:
    padded = f"  {value}  "
    return {padded[index : index + 3] for index in range(len(padded) - 2)} if value else set()


def trigram_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0

    left_trigrams = trigram_set(left)
    right_trigrams = trigram_set(right)
    if not left_trigrams or not right_trigrams:
        return 0.0

    overlap = len(left_trigrams & right_trigrams)
    return (2 * overlap) / (len(left_trigrams) + len(right_trigrams))


class IcdSearchResult:
    def __init__(
        self,
        *,
        code: str,
        description: str,
        category: str | None,
        score: float,
    ) -> None:
        self.code = code
        self.description = description
        self.category = category
        self.score = round(score, 4)


class IcdService:
    def service_status(self) -> str:
        return "ok"

    async def search_codes(
        self,
        session: AsyncSession,
        query: str,
        *,
        limit: int = 10,
    ) -> list[IcdSearchResult]:
        normalized_query = normalize_search_text(query)
        if not normalized_query:
            raise ValueError("Search query cannot be empty.")

        query_tokens = set(normalized_query.split())
        normalized_query_code = normalize_code(query)

        codes = (await session.scalars(select(Icd10Code))).all()
        ranked: list[IcdSearchResult] = []

        for icd_code in codes:
            score = self._score_code(
                icd_code,
                normalized_query=normalized_query,
                normalized_query_code=normalized_query_code,
                query_tokens=query_tokens,
            )
            if score <= 0:
                continue

            ranked.append(
                IcdSearchResult(
                    code=icd_code.code,
                    description=icd_code.description,
                    category=icd_code.category,
                    score=score,
                )
            )

        ranked.sort(key=lambda item: (-item.score, item.code))
        return ranked[:limit]

    def _score_code(
        self,
        icd_code: Icd10Code,
        *,
        normalized_query: str,
        normalized_query_code: str,
        query_tokens: set[str],
    ) -> float:
        normalized_description = normalize_search_text(icd_code.description)
        normalized_search_text = normalize_search_text(icd_code.search_text)
        normalized_code = normalize_code(icd_code.code)

        score = 0.0

        if normalized_query_code and normalized_code == normalized_query_code:
            score += 5.0
        elif normalized_query_code and normalized_code.startswith(normalized_query_code):
            score += 2.0

        if normalized_query in normalized_description:
            score += 3.5

        if normalized_query in normalized_search_text:
            score += 3.0

        if query_tokens:
            description_tokens = set(normalized_description.split())
            search_tokens = set(normalized_search_text.split())
            token_overlap = len(query_tokens & search_tokens) / len(query_tokens)
            description_overlap = len(query_tokens & description_tokens) / len(query_tokens)
            score += token_overlap * 2.0
            score += description_overlap * 1.5

            if query_tokens.issubset(search_tokens):
                score += 1.0

        score += trigram_similarity(normalized_query, normalized_search_text) * 2.2
        score += trigram_similarity(normalized_query, normalized_description) * 1.6
        score += trigram_similarity(normalized_query_code, normalized_code) * 0.8

        if score < 0.45:
            return 0.0

        return score
