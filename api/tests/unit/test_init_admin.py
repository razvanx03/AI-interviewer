import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import verify_password
from models.user import User
from db.init_admin import ensure_initial_admin


class TestInitAdmin:
    """Tests for idempotent initial admin account creation and synchronization."""

    async def test_ensure_initial_admin_creates_or_updates(self, db_session: AsyncSession, monkeypatch):
        test_email = "test_autoseed_admin_2026@test.com"
        test_password = "SuperSecretPassword2026!"

        monkeypatch.setattr(settings, "ADMIN_EMAIL", test_email)
        monkeypatch.setattr(settings, "ADMIN_PASSWORD", test_password)

        try:
            # 1. Run ensure_initial_admin (creates new user)
            await ensure_initial_admin()

            # Verify user was created in DB
            db_session.expire_all()
            stmt = select(User).where(User.email == test_email)
            res = await db_session.execute(stmt)
            user = res.scalar_one_or_none()

            assert user is not None
            assert user.email == test_email
            assert user.role == "admin"
            assert user.is_active is True
            assert verify_password(test_password, user.hashed_password) is True

            # 2. Test idempotency and password update
            updated_password = "NewlyChangedPassword2026!"
            monkeypatch.setattr(settings, "ADMIN_PASSWORD", updated_password)

            await ensure_initial_admin()

            # Re-fetch user with refreshed session cache
            db_session.expire_all()
            res = await db_session.execute(stmt)
            user_updated = res.scalar_one_or_none()
            assert user_updated is not None
            assert verify_password(updated_password, user_updated.hashed_password) is True

        finally:
            # Guaranteed cleanup of test user
            db_session.expire_all()
            stmt = select(User).where(User.email == test_email)
            res = await db_session.execute(stmt)
            u = res.scalar_one_or_none()
            if u:
                await db_session.delete(u)
                await db_session.commit()
