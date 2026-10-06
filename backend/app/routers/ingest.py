"""Agent → server yo'nalishi. Agent kaliti bilan himoyalangan."""
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from ..auth import require_agent_key
from ..config import settings
from ..database import get_session
from ..models import Agent, Event, Screenshot, CapturedFile, Policy, Detection, utcnow
from ..schemas import HelloIn, HelloOut, EventsBatchIn
from ..detection import scan_text
from ..ocr import is_image, extract_text


def _policy(session: Session) -> Policy:
    p = session.get(Policy, 1)
    if p is None:
        p = Policy(id=1)
        session.add(p)
        session.commit()
        session.refresh(p)
    return p


def _scan(session: Session, text: str) -> list[dict]:
    p = _policy(session)
    keywords = [k for k in p.keywords.split(",") if k.strip()]
    return scan_text(text, keywords, p.detect_cards, p.detect_passport)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"], dependencies=[Depends(require_agent_key)])


def _get_or_create_agent(session: Session, agent_uid: str, **fields) -> Agent:
    agent = session.exec(select(Agent).where(Agent.agent_uid == agent_uid)).first()
    if agent is None:
        agent = Agent(agent_uid=agent_uid, hostname=fields.get("hostname") or "unknown")
        session.add(agent)
    for key, value in fields.items():
        if value is not None:
            setattr(agent, key, value)
    agent.last_seen = utcnow()
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.post("/hello", response_model=HelloOut)
def hello(payload: HelloIn, session: Session = Depends(get_session)):
    """Agent ishga tushganda va vaqti-vaqti bilan o'zini bildiradi."""
    agent = _get_or_create_agent(
        session, payload.agent_uid,
        hostname=payload.hostname, full_name=payload.full_name,
        ip_address=payload.ip_address, os_name=payload.os_name,
        agent_version=payload.agent_version,
    )
    return HelloOut(agent_id=agent.id)


@router.post("/events")
def ingest_events(payload: EventsBatchIn, session: Session = Depends(get_session)):
    """Agent to'plagan hodisalarni paket (batch) holida yuboradi."""
    agent = session.exec(select(Agent).where(Agent.agent_uid == payload.agent_uid)).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Avval /hello orqali ro'yxatdan o'ting")

    count, alerts = 0, 0
    for ev in payload.events:
        details = dict(ev.details)
        severity = ev.severity
        matches = _scan(session, " ".join(filter(None, [ev.text, ev.title])))
        if matches:
            severity = "crit"
            details["dlp"] = matches
        row = Event(
            agent_id=agent.id, type=ev.type, channel=ev.channel, severity=severity,
            app=ev.app, title=ev.title, text=ev.text, details=details,
            occurred_at=ev.occurred_at or utcnow(),
        )
        session.add(row)
        count += 1
        if matches:
            session.flush()  # row.id olish uchun
            session.add(Detection(
                agent_id=agent.id, source="event", ref_id=row.id,
                kinds=",".join(sorted({m["kind"] for m in matches})),
                snippet="; ".join(m["sample"] for m in matches)[:200],
            ))
            alerts += 1
    agent.last_seen = utcnow()
    session.add(agent)
    session.commit()
    return {"accepted": count, "alerts": alerts}


@router.post("/screenshot")
async def ingest_screenshot(
    agent_uid: str = Form(...),
    app: str = Form(default=""),
    title: str = Form(default=""),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Ekran suratini qabul qiladi va saqlaydi."""
    agent = session.exec(select(Agent).where(Agent.agent_uid == agent_uid)).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Avval /hello orqali ro'yxatdan o'ting")

    os.makedirs(settings.media_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe = f"{agent.id}_{ts}_{uuid.uuid4().hex[:8]}.jpg"
    dest = os.path.join(settings.media_dir, safe)
    with open(dest, "wb") as out:
        out.write(await file.read())

    session.add(Screenshot(agent_id=agent.id, path=safe, app=app or None, title=title or None))
    agent.last_seen = utcnow()
    session.add(agent)
    session.commit()
    return {"saved": safe}


@router.post("/file")
async def ingest_file(
    agent_uid: str = Form(...),
    filename: str = Form(...),
    channel: str = Form(default=""),
    severity: str = Form(default="info"),
    source_path: str = Form(default=""),
    source_url: str = Form(default=""),
    context_app: str = Form(default=""),
    context_title: str = Form(default=""),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Agent ushlagan faylni qabul qiladi va saqlaydi (panelda o'qish uchun)."""
    agent = session.exec(select(Agent).where(Agent.agent_uid == agent_uid)).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Avval /hello orqali ro'yxatdan o'ting")

    files_dir = os.path.join(settings.media_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = os.path.basename(filename) or "file"
    safe_name = f"{agent.id}_{ts}_{uuid.uuid4().hex[:8]}_{base}"
    dest = os.path.join(files_dir, safe_name)
    content = await file.read()
    with open(dest, "wb") as out:
        out.write(content)

    # Mazmunni maxfiy ma'lumotga tekshirish: matnli fayl — to'g'ridan-to'g'ri,
    # rasm (clipboard rasmi / yuklab olinган rasm) — OCR orqali.
    matches = []
    via_ocr = False
    is_text = (file.content_type or "").startswith("text/") or base.lower().endswith((".txt", ".csv", ".log", ".json", ".md"))
    if is_text:
        try:
            matches = _scan(session, content.decode("utf-8", errors="ignore"))
        except Exception:  # noqa: BLE001
            matches = []
    elif is_image(file.content_type, base):
        ocr_text = await run_in_threadpool(extract_text, content)   # bloklamaslik uchun
        if ocr_text:
            matches = _scan(session, ocr_text)
            via_ocr = True
    if matches:
        severity = "crit"

    cf = CapturedFile(
        agent_id=agent.id, filename=base, path=f"files/{safe_name}",
        source_path=source_path or None, source_url=source_url or None,
        context_app=context_app or None, context_title=context_title or None,
        size=len(content), mime=file.content_type, channel=channel or None, severity=severity,
    )
    session.add(cf)
    if matches:
        session.flush()
        snippet = "; ".join(m["sample"] for m in matches)[:200]
        if via_ocr:
            snippet = f"[OCR] {snippet}"   # rasmдан o'qilganini bildiradi
        session.add(Detection(
            agent_id=agent.id, source="file", ref_id=cf.id,
            kinds=",".join(sorted({m["kind"] for m in matches})),
            snippet=snippet,
        ))
    agent.last_seen = utcnow()
    session.add(agent)
    session.commit()
    return {"saved": safe_name, "size": len(content), "detections": len(matches), "ocr": via_ocr}
