from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.auth import DbSession, clear_session, get_current_user, password_hash, set_session
from app.models import User
from app.schemas import LoginInput, SignupInput, UserResponse

router = APIRouter(prefix="/api/auth", tags=["authentication"])
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupInput, db: DbSession) -> User:
    try:
        existing = db.scalar(select(User).where(func.lower(User.email) == payload.email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists.")
        user = User(name=payload.name, email=payload.email, password_hash=password_hash.hash(payload.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create account.") from exc


@router.post("/login", response_model=UserResponse)
def login(payload: LoginInput, response: Response, db: DbSession) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email))
    if user is None or not password_hash.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    set_session(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session(response)


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> User:
    return current_user
