"""Agentni avtomatik yangilash.

- Agent (X-API-Key bilan): eng yangi versiyani so'raydi va exe'ni yuklab oladi.
- Superadmin (token bilan): yangi reliz yuklaydi va ro'yxatni ko'radi.

Xavfsizlik: yuklab olish agent kaliti bilan himoyalangan; agent SHA256 ni tekshiradi.
Ishlab chiqarishда exe kod imzolash sertifikati bilan ham imzolanishi kerak.
"""
import hashlib
import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ..auth import require_agent_key, require_role
from ..audit import record
from ..config import settings
from ..database import get_session
from ..models import AgentRelease
from ..schemas import VersionOut, ReleaseOut

router = APIRouter(prefix="/api/v1/agent", tags=["updates"])


def _parse(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:  # noqa: BLE001
        return (0,)


def _latest(session: Session) -> AgentRelease | None:
    rows = session.exec(select(AgentRelease)).all()
    return max(rows, key=lambda r: _parse(r.version)) if rows else None


# ---------- Agent tomoni (X-API-Key) ----------
@router.get("/version", response_model=VersionOut, dependencies=[Depends(require_agent_key)])
def latest_version(session: Session = Depends(get_session)):
    rel = _latest(session)
    if not rel:
        return VersionOut()
    return VersionOut(version=rel.version, sha256=rel.sha256,
                      url=f"/api/v1/agent/download/{rel.version}", notes=rel.notes)


@router.get("/download/{version}", dependencies=[Depends(require_agent_key)])
def download(version: str, session: Session = Depends(get_session)):
    rel = session.exec(select(AgentRelease).where(AgentRelease.version == version)).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Bunday versiya yo'q")
    full = os.path.join(settings.media_dir, rel.path)
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    return FileResponse(full, filename=rel.filename, media_type="application/octet-stream")


# ---------- Superadmin tomoni (token) ----------
@router.get("/releases", response_model=list[ReleaseOut])
def list_releases(ctx: dict = Depends(require_role("admin", "auditor")), session: Session = Depends(get_session)):
    rows = session.exec(select(AgentRelease).order_by(AgentRelease.created_at.desc())).all()
    return rows


@router.post("/releases", response_model=ReleaseOut)
async def upload_release(
    version: str = Form(...),
    notes: str = Form(default=""),
    file: UploadFile = File(...),
    ctx: dict = Depends(require_role("superadmin")),
    session: Session = Depends(get_session),
):
    if session.exec(select(AgentRelease).where(AgentRelease.version == version)).first():
        raise HTTPException(status_code=400, detail="Bu versiya allaqachon mavjud")

    rel_dir = os.path.join(settings.media_dir, "agent")
    os.makedirs(rel_dir, exist_ok=True)
    content = await file.read()
    sha = hashlib.sha256(content).hexdigest()
    safe = f"hp-dlp-agent-{version}-{uuid.uuid4().hex[:6]}.exe"
    with open(os.path.join(rel_dir, safe), "wb") as out:
        out.write(content)

    rel = AgentRelease(version=version, filename=f"hp-dlp-agent-{version}.exe",
                       path=f"agent/{safe}", sha256=sha, notes=notes or None)
    session.add(rel)
    record(session, ctx.get("u"), "release_upload", version)
    session.commit()
    session.refresh(rel)
    return rel
