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
from db.crud import get_user_by_username, get_user_by_email, create_user
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


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


# ── Register ───────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new LexAI user account.
    Returns the created user (no token — user must login after registration).
    """
    # Check username taken
    if await get_user_by_username(db, req.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    # Check email taken
    if await get_user_by_email(db, req.email):
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
            username=req.username,
            email=req.email,
            hashed_password=hashed_password,
        )
    except OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is temporarily busy. Please retry in a moment.",
        ) from exc
    return UserResponse(id=user.id, username=user.username, email=user.email)


# ── Login ──────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate and return a JWT bearer token.
    Accepts standard OAuth2 form: username + password fields.
    """
    user = await get_user_by_username(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    token = create_access_token({"sub": user.username})
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
