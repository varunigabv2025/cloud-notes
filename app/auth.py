import base64
import hashlib
import hmac
import os
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

password_hash = PasswordHash.recommended()
DbSession = Annotated[Session, Depends(get_db)]
SESSION_COOKIE = "cloud_notes_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7


def get_secret_key() -> str:
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY must be set before starting Cloud Notes.")
    return secret_key


def _signature(payload: str) -> str:
    return hmac.new(get_secret_key().encode(), payload.encode(), hashlib.sha256).hexdigest()


def _cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "false").lower() == "true"


def set_session(response: Response, user_id: int) -> None:
    payload = f"{user_id}.{int(time.time())}"
    value = base64.urlsafe_b64encode(f"{payload}.{_signature(payload)}".encode()).decode()
    response.set_cookie(SESSION_COOKIE, value, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax", secure=_cookie_secure())


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax", secure=_cookie_secure())


def session_user_id(request: Request) -> int | None:
    value = request.cookies.get(SESSION_COOKIE)
    if not value:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value.encode()).decode()
        user_id_text, issued_at_text, signature = decoded.split(".", maxsplit=2)
        payload = f"{user_id_text}.{issued_at_text}"
        if not hmac.compare_digest(signature, _signature(payload)) or int(issued_at_text) + SESSION_MAX_AGE < time.time():
            return None
        return int(user_id_text)
    except (ValueError, UnicodeDecodeError):
        return None


def get_current_user(request: Request, db: DbSession) -> User:
    user_id = session_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in.")
    return user
