"""Audit jurnaliga yozish yordamchisi."""
from sqlmodel import Session

from .models import AuditLog


def record(session: Session, actor: str, action: str, target: str | None = None) -> None:
    session.add(AuditLog(actor=actor or "—", action=action, target=target))
    # commit chaqiruvchi tomonda bo'ladi
