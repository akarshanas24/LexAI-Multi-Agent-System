"""
Authentication helpers using only the Python standard library.
"""

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from db.database import get_db
from db.crud import get_user_by_username
from db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
MAX_PASSWORD_BYTES = 256
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16

try:
    from jose import JWTError, jwt
except ModuleNotFoundError:  # pragma: no cover
    class JWTError(Exception):
        pass

    jwt = None


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def hash_password(plain: str) -> str:
    password_bytes = plain.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password cannot be longer than {MAX_PASSWORD_BYTES} bytes"
        )
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(plain: str, hashed: str) -> bool:
    password_bytes = plain.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False
    try:
        scheme, iterations, salt, digest = hashed.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            password_bytes,
            _b64decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(_b64encode(expected), digest)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire})
    if jwt is None:
        normalized = payload.copy()
        normalized["exp"] = int(expire.replace(tzinfo=timezone.utc).timestamp())
        body = _b64encode(
            json.dumps(normalized, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            body.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        return f"{body}.{signature}"
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    if jwt is None:
        try:
            body, signature = token.split(".", 1)
        except ValueError as exc:
            raise JWTError("Malformed token") from exc

        expected = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            body.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise JWTError("Invalid signature")

        payload = json.loads(_b64decode(body))
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise JWTError("Token expired")
        return payload
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
        if not username:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = await get_user_by_username(db, username)
    if not user or not user.is_active:
        raise credentials_exc
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
