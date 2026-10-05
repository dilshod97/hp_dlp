"""Panel → server yo'nalishi (asosan o'qish). Token bilan himoyalangan.

Ro'yxatlar sahifalanadi: {items, total, limit, offset}.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select, func

import os

from ..auth import require_dashboard, require_role
from ..audit import record
from ..config import settings
from ..database import get_session
from ..models import Agent, Event, Screenshot, CapturedFile, Detection, Policy, AuditLog, utcnow
from ..schemas import (
    AgentOut, EventOut, OverviewOut, ScreenshotOut, AgentUpdate, FileOut,
    DetectionOut, PolicyOut, PolicyUpdate, AuditOut,
)

router = APIRouter(prefix="/api/v1", tags=["dashboard"], dependencies=[Depends(require_dashboard)])

ONLINE_WINDOW = timedelta(minutes=5)


def _count(session: Session, model) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


# ---------- Agentlar ----------
@router.get("/agents")
def list_agents(limit: int = Query(50, le=200), offset: int = 0, session: Session = Depends(get_session)):
    total = _count(session, Agent)
    rows = session.exec(select(Agent).order_by(Agent.last_seen.desc()).offset(offset).limit(limit)).all()
    items = [AgentOut.model_validate(a, from_attributes=True) for a in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.patch("/agents/{agent_id}", response_model=AgentOut)
def update_agent(agent_id: int, payload: AgentUpdate, ctx: dict = Depends(require_role("admin")), session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent topilmadi")
    if payload.display_name is not None:
        agent.display_name = payload.display_name.strip() or None
    if payload.note is not None:
        agent.note = payload.note.strip() or None
    if payload.active is not None:
        agent.active = payload.active
    session.add(agent)
    record(session, ctx.get("u"), "agent_update", f"{agent.hostname} → {agent.display_name or '—'}")
    session.commit()
    session.refresh(agent)
    return agent


# ---------- Hodisalar ----------
def _day_bounds(day: str):
    """'YYYY-MM-DD' -> (kun boshi, kun oxiri) UTC."""
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


@router.get("/events")
def list_events(
    limit: int = Query(50, le=200), offset: int = 0,
    severity: str | None = None, type: str | None = None, types: str | None = None,
    day: str | None = None, app: str | None = None,
    session: Session = Depends(get_session),
):
    conds = []
    if severity:
        conds.append(Event.severity == severity)
    if type:
        conds.append(Event.type == type)
    if app:
        conds.append(Event.app == app)
    if types:
        wanted = [t.strip() for t in types.split(",") if t.strip()]
        if wanted:
            conds.append(Event.type.in_(wanted))
    if day:
        try:
            s, e = _day_bounds(day)
            conds.append(Event.occurred_at >= s)
            conds.append(Event.occurred_at < e)
        except ValueError:
            pass
    base = select(Event)
    cnt = select(func.count()).select_from(Event)
    for c in conds:
        base = base.where(c)
        cnt = cnt.where(c)
    total = session.exec(cnt).one()
    rows = session.exec(base.order_by(Event.occurred_at.desc()).offset(offset).limit(limit)).all()
    items = [EventOut.model_validate(e, from_attributes=True) for e in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------- Skrinshotlar ----------
@router.get("/screenshots")
def list_screenshots(limit: int = Query(40, le=200), offset: int = 0, session: Session = Depends(get_session)):
    total = _count(session, Screenshot)
    rows = session.exec(select(Screenshot).order_by(Screenshot.occurred_at.desc()).offset(offset).limit(limit)).all()
    items = [ScreenshotOut(id=s.id, agent_id=s.agent_id, url=f"/media/{s.path}", app=s.app, title=s.title, occurred_at=s.occurred_at) for s in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------- Fayllar ----------
@router.get("/files/{file_id}", response_model=FileOut)
def open_file(file_id: int, ctx: dict = Depends(require_dashboard), session: Session = Depends(get_session)):
    """Faylni ochish — audit jurnaliga 'kim ko'rdi' yoziladi."""
    f = session.get(CapturedFile, file_id)
    if not f:
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    record(session, ctx.get("u"), "file_view", f.filename)
    session.commit()
    return FileOut(id=f.id, agent_id=f.agent_id, filename=f.filename, url=f"/media/{f.path}",
                   source_path=f.source_path, size=f.size, mime=f.mime, channel=f.channel,
                   severity=f.severity, occurred_at=f.occurred_at)


@router.get("/files")
def list_files(limit: int = Query(50, le=200), offset: int = 0, session: Session = Depends(get_session)):
    total = _count(session, CapturedFile)
    rows = session.exec(select(CapturedFile).order_by(CapturedFile.occurred_at.desc()).offset(offset).limit(limit)).all()
    items = [FileOut(id=f.id, agent_id=f.agent_id, filename=f.filename, url=f"/media/{f.path}", source_path=f.source_path, size=f.size, mime=f.mime, channel=f.channel, severity=f.severity, occurred_at=f.occurred_at) for f in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------- Aniqlashlar (DLP) ----------
@router.get("/detections")
def list_detections(limit: int = Query(50, le=200), offset: int = 0, session: Session = Depends(get_session)):
    total = _count(session, Detection)
    rows = session.exec(select(Detection).order_by(Detection.occurred_at.desc()).offset(offset).limit(limit)).all()
    items = [DetectionOut.model_validate(d, from_attributes=True) for d in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------- Siyosat ----------
@router.get("/policy", response_model=PolicyOut)
def get_policy(session: Session = Depends(get_session)):
    p = session.get(Policy, 1) or Policy(id=1)
    return PolicyOut.model_validate(p, from_attributes=True)


@router.put("/policy", response_model=PolicyOut)
def update_policy(payload: PolicyUpdate, ctx: dict = Depends(require_role("admin")), session: Session = Depends(get_session)):
    p = session.get(Policy, 1)
    if p is None:
        p = Policy(id=1)
        session.add(p)
    for field in ("keywords", "detect_cards", "detect_passport", "block_usb", "retention_days"):
        val = getattr(payload, field)
        if val is not None:
            setattr(p, field, val)
    p.updated_at = utcnow()
    session.add(p)
    record(session, ctx.get("u"), "policy_update", None)
    session.commit()
    session.refresh(p)
    return PolicyOut.model_validate(p, from_attributes=True)


# ---------- Audit jurnali ----------
@router.get("/audit")
def list_audit(limit: int = Query(50, le=200), offset: int = 0,
               ctx: dict = Depends(require_role("admin", "auditor")), session: Session = Depends(get_session)):
    total = _count(session, AuditLog)
    rows = session.exec(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)).all()
    items = [AuditOut.model_validate(a, from_attributes=True) for a in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ---------- Ma'lumotni tozalash (saqlash muddati) ----------
@router.post("/maintenance/cleanup")
def cleanup(days: int | None = None, ctx: dict = Depends(require_role("superadmin")), session: Session = Depends(get_session)):
    """Saqlash muddatidan oshgan ma'lumotlarni o'chiradi."""
    p = session.get(Policy, 1)
    retention = days or (p.retention_days if p else 90)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention)

    # Fayllarni diskdan ham o'chirish
    old_files = session.exec(select(CapturedFile).where(CapturedFile.occurred_at < cutoff)).all()
    old_shots = session.exec(select(Screenshot).where(Screenshot.occurred_at < cutoff)).all()
    removed_files = 0
    for f in old_files + old_shots:
        try:
            os.remove(os.path.join(settings.media_dir, f.path))
            removed_files += 1
        except OSError:
            pass

    counts = {}
    for model, field in [(Event, Event.occurred_at), (Detection, Detection.occurred_at),
                         (CapturedFile, CapturedFile.occurred_at), (Screenshot, Screenshot.occurred_at)]:
        rows = session.exec(select(model).where(field < cutoff)).all()
        counts[model.__name__] = len(rows)
        for r in rows:
            session.delete(r)
    record(session, ctx.get("u"), "cleanup", f"{retention} kun")
    session.commit()
    return {"retention_days": retention, "deleted": counts, "media_removed": removed_files}


# ---------- Statistika ----------
@router.get("/stats/overview", response_model=OverviewOut)
def overview(session: Session = Depends(get_session)):
    now = datetime.now(timezone.utc)
    day_start = now - timedelta(hours=24)
    online_since = now - ONLINE_WINDOW

    def cnt(model, *conds):
        q = select(func.count()).select_from(model)
        for c in conds:
            q = q.where(c)
        return session.exec(q).one()

    return OverviewOut(
        agents_total=cnt(Agent),
        agents_online=cnt(Agent, Agent.last_seen >= online_since),
        events_today=cnt(Event, Event.occurred_at >= day_start),
        alerts_today=cnt(Event, Event.occurred_at >= day_start, Event.severity.in_(["warn", "crit"])),
        detections_today=cnt(Detection, Detection.occurred_at >= day_start),
    )


@router.get("/stats/event-types")
def event_types(hours: int = Query(24, le=720), session: Session = Depends(get_session)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = session.exec(
        select(Event.type, func.count()).where(Event.occurred_at >= cutoff).group_by(Event.type)
    ).all()
    return [{"type": t, "count": c} for t, c in sorted(rows, key=lambda x: -x[1])]


@router.get("/stats/worktime")
def worktime(day: str | None = None, session: Session = Depends(get_session)):
    """Har bir agent uchun ish vaqti: boshlanish, tugash, faol vaqt, hodisalar soni."""
    if day:
        try:
            start, end = _day_bounds(day)
        except ValueError:
            start = datetime.now(timezone.utc) - timedelta(hours=24); end = datetime.now(timezone.utc)
    else:
        start, end = _day_bounds(datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    rows = session.exec(select(Event).where(Event.occurred_at >= start, Event.occurred_at < end)).all()
    agents = {a.id: (a.display_name or a.full_name or a.hostname) for a in session.exec(select(Agent)).all()}
    by_agent: dict[int, dict] = {}
    for e in rows:
        g = by_agent.setdefault(e.agent_id, {"first": e.occurred_at, "last": e.occurred_at, "active_seconds": 0, "events": 0})
        if e.occurred_at < g["first"]:
            g["first"] = e.occurred_at
        if e.occurred_at > g["last"]:
            g["last"] = e.occurred_at
        g["events"] += 1
        if e.type == "active_window" and isinstance(e.details, dict):
            g["active_seconds"] += e.details.get("duration_sec", 0) or 0

    out = []
    for aid, g in by_agent.items():
        out.append({
            "agent_id": aid, "name": agents.get(aid, f"#{aid}"),
            "first": g["first"], "last": g["last"],
            "active_seconds": g["active_seconds"], "events": g["events"],
        })
    return sorted(out, key=lambda x: x["name"])


@router.get("/stats/app-usage")
def app_usage(hours: int = Query(24, le=720), agent_id: int | None = None, session: Session = Depends(get_session)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = select(Event).where(Event.type == "active_window", Event.occurred_at >= cutoff)
    if agent_id:
        q = q.where(Event.agent_id == agent_id)
    rows = session.exec(q.limit(5000)).all()
    totals: dict[str, dict] = {}
    for e in rows:
        app = e.app or "—"
        sec = 0
        if isinstance(e.details, dict):
            sec = e.details.get("duration_sec", 0) or 0
        t = totals.setdefault(app, {"seconds": 0, "count": 0})
        t["seconds"] += sec
        t["count"] += 1
    out = [{"app": a, "seconds": v["seconds"], "count": v["count"]} for a, v in totals.items()]
    return sorted(out, key=lambda x: -x["seconds"])


@router.get("/stats/message-apps")
def message_apps(session: Session = Depends(get_session)):
    """Yozishmаларда uchragan dasturlar ro'yxati (filter uchun)."""
    rows = session.exec(
        select(Event.app).where(Event.type.in_(["keyboard", "clipboard", "telegram", "email"]),
                                Event.app.is_not(None)).distinct()
    ).all()
    return sorted({a for a in rows if a})


@router.get("/stats/site-usage")
def site_usage(hours: int = Query(24, le=720), agent_id: int | None = None, session: Session = Depends(get_session)):
    """Veb-saytlarда o'tkazilgan vaqt (masalan kun.uz'da qancha)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = select(Event).where(Event.type == "web", Event.occurred_at >= cutoff)
    if agent_id:
        q = q.where(Event.agent_id == agent_id)
    rows = session.exec(q.limit(5000)).all()
    totals: dict[str, dict] = {}
    for e in rows:
        site = e.title or "—"
        sec = e.details.get("duration_sec", 0) if isinstance(e.details, dict) else 0
        t = totals.setdefault(site, {"seconds": 0, "count": 0})
        t["seconds"] += sec or 0
        t["count"] += 1
    out = [{"site": s, "seconds": v["seconds"], "count": v["count"]} for s, v in totals.items()]
    return sorted(out, key=lambda x: -x["seconds"])
