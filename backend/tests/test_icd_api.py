import pytest

from app.core.security import hash_password
from app.db.models.enums import UserRole
from app.db.models.icd10_code import Icd10Code
from app.db.models.provider_profile import ProviderProfile
from app.db.models.user import User


def create_provider(email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("DemoPass123!"),
        role=UserRole.PROVIDER,
        is_active=True,
    )
    user.provider_profile = ProviderProfile(
        first_name="Maya",
        last_name="Chen",
        specialty="Family Medicine",
    )
    return user


@pytest.mark.asyncio
async def test_icd_search_requires_authentication(client) -> None:
    response = await client.get("/api/icd/search", params={"q": "knee arthritis"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_icd_search_returns_ranked_results(client, db_session) -> None:
    provider = create_provider("icd-search@example.com")
    db_session.add(provider)
    db_session.add_all(
        [
            Icd10Code(
                code="M17.11",
                description="Unilateral primary osteoarthritis, right knee",
                category="Musculoskeletal",
                search_text="m17 11 unilateral primary osteoarthritis right knee right knee arthritis knee osteoarthritis",
            ),
            Icd10Code(
                code="M25.561",
                description="Pain in right knee",
                category="Musculoskeletal",
                search_text="m25 561 pain in right knee right knee pain knee pain",
            ),
            Icd10Code(
                code="J02.9",
                description="Acute pharyngitis, unspecified",
                category="Respiratory",
                search_text="j02 9 acute pharyngitis unspecified sore throat",
            ),
        ]
    )
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "icd-search@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.get("/api/icd/search", params={"q": "right knee arthritis"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2
    assert body[0]["code"] == "M17.11"
    assert body[0]["score"] >= body[1]["score"]


@pytest.mark.asyncio
async def test_icd_search_rejects_blank_query_after_trimming(client, db_session) -> None:
    provider = create_provider("icd-blank@example.com")
    db_session.add(provider)
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "icd-blank@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.get("/api/icd/search", params={"q": "   "})

    assert response.status_code == 422
    assert response.json()["detail"] == "Search query cannot be empty."


@pytest.mark.asyncio
async def test_icd_search_honors_result_limit(client, db_session) -> None:
    provider = create_provider("icd-limit@example.com")
    db_session.add(provider)
    for index in range(5):
        db_session.add(
            Icd10Code(
                code=f"M25.56{index}",
                description=f"Pain in right knee variant {index}",
                category="Musculoskeletal",
                search_text=f"m25 56{index} pain in right knee variant {index} right knee pain knee pain",
            )
        )
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "icd-limit@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.get("/api/icd/search", params={"q": "knee pain", "limit": 3})

    assert response.status_code == 200
    assert len(response.json()) == 3
