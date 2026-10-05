"""Foydalanuvchilar boshqaruvi — faqat superadmin."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_role, hash_password
from ..audit import record
from ..database import get_session
from ..models import User
from ..schemas import UserOut, UserCreate, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])

ROLES = {"superadmin", "admin", "operator", "auditor"}


@router.get("", response_model=list[UserOut])
def list_users(ctx: dict = Depends(require_role("superadmin")), session: Session = Depends(get_session)):
    return session.exec(select(User).order_by(User.id)).all()


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, ctx: dict = Depends(require_role("superadmin")), session: Session = Depends(get_session)):
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="Noto'g'ri rol")
    if session.exec(select(User).where(User.username == payload.username)).first():
        raise HTTPException(status_code=400, detail="Bunday login mavjud")
    user = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
    session.add(user)
    record(session, ctx.get("u"), "user_create", payload.username)
    session.commit()
    session.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, ctx: dict = Depends(require_role("superadmin")), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.role:
        if payload.role not in ROLES:
            raise HTTPException(status_code=400, detail="Noto'g'ri rol")
        user.role = payload.role
    if payload.active is not None:
        user.active = payload.active
    session.add(user)
    record(session, ctx.get("u"), "user_update", user.username)
    session.commit()
    session.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, ctx: dict = Depends(require_role("superadmin")), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    if user.username == ctx.get("u"):
        raise HTTPException(status_code=400, detail="O'zingizni o'chira olmaysiz")
    name = user.username
    session.delete(user)
    record(session, ctx.get("u"), "user_delete", name)
    session.commit()
    return {"deleted": name}
