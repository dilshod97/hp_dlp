"""Panelga kirish: foydalanuvchi/parol -> token."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import verify_password, make_token, require_dashboard
from ..audit import record
from ..database import get_session
from ..models import User
from ..schemas import LoginIn, TokenOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == payload.username)).first()
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
    record(session, user.username, "login", None)
    session.commit()
    return TokenOut(token=make_token(user.username, user.role), username=user.username, role=user.role)


@router.get("/me")
def me(ctx: dict = Depends(require_dashboard)):
    return {"username": ctx.get("u"), "role": ctx.get("r")}
