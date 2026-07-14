import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from app.core.security import hash_password
from app.db.models.provider_profile import ProviderProfile
from app.db.models.user import User
from app.db.models.enums import UserRole


@pytest.mark.asyncio
async def test_user_email_is_normalized_to_lowercase(db_session) -> None:
    user = User(
        email="  PROVIDER@Example.COM  ",
        password_hash=hash_password("DemoPass123!"),
        role=UserRole.PROVIDER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.email == "provider@example.com"


@pytest.mark.asyncio
async def test_duplicate_email_is_rejected(db_session) -> None:
    first_user = User(
        email="provider@example.com",
        password_hash=hash_password("DemoPass123!"),
        role=UserRole.PROVIDER,
        is_active=True,
    )
    duplicate_user = User(
        email="PROVIDER@example.com",
        password_hash=hash_password("AnotherPass123!"),
        role=UserRole.PROVIDER,
        is_active=True,
    )

    db_session.add(first_user)
    await db_session.commit()

    db_session.add(duplicate_user)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_password_hash_is_not_plaintext(db_session) -> None:
    plain_password = "DemoPass123!"
    user = User(
        email="hashcheck@example.com",
        password_hash=hash_password(plain_password),
        role=UserRole.PROVIDER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.password_hash != plain_password


@pytest.mark.asyncio
async def test_invalid_user_role_is_rejected(db_session) -> None:
    user = User(
        email="invalid-role@example.com",
        password_hash=hash_password("DemoPass123!"),
        role="super_admin",  # type: ignore[arg-type]
        is_active=True,
    )
    db_session.add(user)

    with pytest.raises((StatementError, IntegrityError, ValueError)):
        await db_session.commit()


@pytest.mark.asyncio
async def test_inactive_user_can_be_identified(db_session) -> None:
    user = User(
        email="inactive@example.com",
        password_hash=hash_password("DemoPass123!"),
        role=UserRole.PROVIDER,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.is_active is False


@pytest.mark.asyncio
async def test_provider_can_have_one_profile(db_session) -> None:
    user = User(
        email="provider.profile@example.com",
        password_hash=hash_password("DemoPass123!"),
        role=UserRole.PROVIDER,
        is_active=True,
    )
    profile = ProviderProfile(
        user=user,
        first_name="Jordan",
        last_name="Test",
        specialty="Family Medicine",
    )
    db_session.add_all([user, profile])
    await db_session.commit()
    await db_session.refresh(user, ["provider_profile"])

    assert user.provider_profile is not None
    assert user.provider_profile.first_name == "Jordan"


@pytest.mark.asyncio
async def test_admin_does_not_require_provider_profile(db_session) -> None:
    admin_user = User(
        email="admin@example.com",
        password_hash=hash_password("DemoPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(admin_user, ["provider_profile"])

    assert admin_user.provider_profile is None


@pytest.mark.asyncio
async def test_duplicate_profiles_for_one_user_are_rejected(db_session) -> None:
    user = User(
        email="duplicate.profile@example.com",
        password_hash=hash_password("DemoPass123!"),
        role=UserRole.PROVIDER,
        is_active=True,
    )
    first_profile = ProviderProfile(
        user=user,
        first_name="Jordan",
        last_name="Test",
        specialty="Internal Medicine",
    )
    second_profile = ProviderProfile(
        user_id=user.id,
        first_name="Jordan",
        last_name="Duplicate",
        specialty=None,
    )

    db_session.add_all([user, first_profile])
    await db_session.commit()

    db_session.add(second_profile)
    with pytest.raises(IntegrityError):
        await db_session.commit()
