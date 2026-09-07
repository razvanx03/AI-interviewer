from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from db.session import get_db
from models.user import User
from schemas.auth import LoginRequest, TokenResponse, UserResponse
from core.security import verify_password, create_access_token
from core.config import settings
from core.deps import get_current_user

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate admin user, issue JWT, and attach HttpOnly cookie."""
    identifier = req.username_or_email.strip().lower()

    # Search by exact email or prefix username matching
    stmt = select(User).where(
        or_(
            User.email.ilike(identifier),
            User.email.ilike(f"{identifier}@%"),
        )
    ).limit(2)
    result = await db.execute(stmt)
    matching_users = result.scalars().all()

    # If 0 users or ambiguous username matching multiple accounts, reject with 401
    if len(matching_users) != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your username/email and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = matching_users[0]

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your username/email and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )

    # Set secure HttpOnly cookie for browser sessions (secure=True in production)
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        secure=is_prod,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )

@router.post("/logout")
async def logout(response: Response):
    """Clear HttpOnly access_token cookie."""
    is_prod = settings.ENVIRONMENT == "production"
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=is_prod,
        samesite="lax",
    )
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Fetch profile of currently authenticated user."""
    return UserResponse.model_validate(current_user)
