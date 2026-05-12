"""
auth/routes.py
==============
Authentication endpoints:

    POST /auth/register  — Create a new user account
    POST /auth/login     — Get a JWT access token
    GET  /auth/me        — Return current user info
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import (
    MAX_PASSWORD_BYTES, hash_password, verify_password,
    create_access_token, get_current_user,
)
from db.database import get_db
from db.crud import (
    create_activity_log,
    get_user_by_username_ci,
    get_user_by_email_ci,
    get_user_by_login_identifier,
    create_user,
)
from db.models import User
from utils.logger import logger

router = APIRouter(prefix="/auth", tags=["auth"])


async def _try_create_activity_log(
    db: AsyncSession,
    user_id: str,
    action: str,
    description: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        await create_activity_log(
            db,
            user_id,
            action,
            description,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )
    except OperationalError:
        logger.warning(
            f"Skipped auth activity log action={action} entity_type={entity_type} "
            f"entity_id={entity_id} because the database was busy."
        )


# ── Schemas ────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str


class ResetPasswordRequest(BaseModel):
    identifier: str
    password: str


# ── Register ───────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new LexAI user account.
    Returns the created user (no token — user must login after registration).
    """
    username = req.username.strip()
    email = req.email.strip().lower()

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Check username taken
    if await get_user_by_username_ci(db, username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check email taken
    if await get_user_by_email_ci(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Enforce minimum password length
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if len(req.password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at most {MAX_PASSWORD_BYTES} bytes",
        )

    try:
        hashed_password = hash_password(req.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        user = await create_user(
            db,
            username=username,
            email=email,
            hashed_password=hashed_password,
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is temporarily busy. Please retry in a moment.",
        ) from exc
    await _try_create_activity_log(
        db,
        user.id,
        "user_registered",
        f"Registered account for {user.username}",
        entity_type="user",
        entity_id=user.id,
        metadata={"email": user.email},
    )
    return UserResponse(id=user.id, username=user.username, email=user.email)


# ── Login ──────────────────────────────────────────────
@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Local recovery helper for development mode.
    Allows resetting a password by username or email without the old password.
    """
    identifier = req.identifier.strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="Username or email is required")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if len(req.password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at most {MAX_PASSWORD_BYTES} bytes",
        )

    user = await get_user_by_login_identifier(db, identifier)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        user.hashed_password = hash_password(req.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await _try_create_activity_log(
        db,
        user.id,
        "password_reset",
        f"Password reset for {user.username}",
        entity_type="user",
        entity_id=user.id,
    )
    return {"message": "Password updated. Sign in with the new password."}


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate and return a JWT bearer token.
    Accepts standard OAuth2 form: username + password fields.
    """
    identifier = form.username.strip()
    user = await get_user_by_login_identifier(db, identifier)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    token = create_access_token({"sub": user.username})
    await _try_create_activity_log(
        db,
        user.id,
        "user_login",
        f"Signed in as {user.username}",
        entity_type="user",
        entity_id=user.id,
    )
    return TokenResponse(access_token=token)


# ── Me ─────────────────────────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
    )
