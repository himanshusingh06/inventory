from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import create_token, get_current_user, hash_password, require_permission, verify_password
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse, UserCreate, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    return {"token": create_token(user), "user": user}


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("users:write")),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserRead)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("users:write")),
):
    user = User(
        store_id=payload.store_id,
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        active=payload.active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
