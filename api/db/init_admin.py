import uuid
import logging
from sqlalchemy import select
from core.config import settings
from core.security import get_password_hash, verify_password
from models.user import User
from db.session import async_session_maker

logger = logging.getLogger("api.db.init_admin")

async def ensure_initial_admin() -> None:
    """
    Ensure the initial administrator account configured in settings (ADMIN_EMAIL / ADMIN_PASSWORD)
    exists and has active admin credentials. Runs automatically and idempotently on startup.
    """
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    admin_password = settings.ADMIN_PASSWORD

    if not admin_email or not admin_password:
        raise RuntimeError("FATAL: ADMIN_EMAIL and ADMIN_PASSWORD must be configured in environment (.env).")

    async with async_session_maker() as session:
        # 1. Check if user with target admin email already exists
        stmt = select(User).where(User.email.ilike(admin_email))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Check if password or role needs updating to match environment settings
            needs_update = False
            if not verify_password(admin_password, user.hashed_password):
                user.hashed_password = get_password_hash(admin_password)
                needs_update = True
            if user.role != "admin" or not user.is_active:
                user.role = "admin"
                user.is_active = True
                needs_update = True

            if needs_update:
                await session.commit()
                logger.info("Updated password/credentials for existing admin user: %s", admin_email)
            else:
                logger.info("Admin user '%s' verified and active.", admin_email)
            return

        # Create fresh admin user if none found
        new_admin = User(
            id=str(uuid.uuid4()),
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            full_name="Lead Recruiter Admin",
            role="admin",
            is_active=True,
        )
        session.add(new_admin)
        await session.commit()
        logger.info("Created initial administrator account from environment: %s", admin_email)
