"""Ma'lumotlar bazasi modellari."""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field, Column, JSON


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agent(SQLModel, table=True):
    """Ro'yxatdan o'tgan bitta kompyuter (agent)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_uid: str = Field(index=True, unique=True)   # agent o'zini tanituvchi UUID
    hostname: str = Field(index=True)                 # avtomatik (agentdan)
    full_name: Optional[str] = None                   # avtomatik (agent sozlamasidan)
    agent_version: Optional[str] = None               # agentning joriy versiyasi
    display_name: Optional[str] = None                # ADMIN qo'lda beradi (asosiy nom)
    note: Optional[str] = None                        # admin izohi (masalan: ishdan bo'shagan sana)
    active: bool = True                               # xodim ishdan bo'shasa -> False
    ip_address: Optional[str] = None
    os_name: Optional[str] = None
    last_seen: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)


class Event(SQLModel, table=True):
    """Agentdan kelgan bitta hodisa (faol oyna, USB, hok.)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(index=True, foreign_key="agent.id")
    type: str = Field(index=True)                 # active_window, usb, print, ...
    channel: Optional[str] = None                 # telegram, email, usb, clipboard...
    severity: str = Field(default="info")         # info, warn, crit
    app: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None                    # klaviatura matni / tavsif
    details: dict = Field(default_factory=dict, sa_column=Column(JSON))
    occurred_at: datetime = Field(default_factory=utcnow, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class User(SQLModel, table=True):
    """Panelga kiradigan admin foydalanuvchi."""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="admin")   # superadmin, admin, operator, auditor
    active: bool = True
    created_at: datetime = Field(default_factory=utcnow)


class CapturedFile(SQLModel, table=True):
    """Agent orqali ushlangan fayl (USB, e-mail, telegram, hok.)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(index=True, foreign_key="agent.id")
    filename: str
    path: str                              # media ichidagi nisbiy yo'l (serverda)
    source_path: Optional[str] = None      # fayl kompyuterda qayerda edi (masalan C:\Users\...\Downloads)
    source_url: Optional[str] = None       # qayerdan yuklangan (brauzer Zone.Identifier)
    context_app: Optional[str] = None      # fayl paydo bo'lganда faol dastur (Chrome/Telegram...)
    context_title: Optional[str] = None    # faol oyna sarlavhasi (Telegram chat nomi / sahifa)
    size: int = 0
    mime: Optional[str] = None
    channel: Optional[str] = None          # usb, file, ...
    severity: str = Field(default="info")
    occurred_at: datetime = Field(default_factory=utcnow, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class Policy(SQLModel, table=True):
    """DLP siyosati — bitta sozlamalar yozuvi (id=1)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    keywords: str = Field(default="maxfiy,confidential,parol,password,secret")
    detect_cards: bool = True
    detect_passport: bool = True
    block_usb: bool = False          # haqiqiy bloklash agent tomonida (keyingi bosqich)
    retention_days: int = 90         # ma'lumotni qancha saqlash
    updated_at: datetime = Field(default_factory=utcnow)


class AgentRelease(SQLModel, table=True):
    """Agentning chiqarilgan versiyasi (avtomatik yangilanish uchun)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    version: str = Field(index=True, unique=True)   # masalan "0.5.0"
    filename: str
    path: str                                       # media ichidagi yo'l
    sha256: str
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class AuditLog(SQLModel, table=True):
    """Admin harakatlari jurnali — kim nima qildi/ko'rdi."""
    id: Optional[int] = Field(default=None, primary_key=True)
    actor: str                        # foydalanuvchi nomi
    action: str                       # login, policy_update, agent_update, user_create, file_view ...
    target: Optional[str] = None      # nimaga nisbatan
    created_at: datetime = Field(default_factory=utcnow, index=True)


class Detection(SQLModel, table=True):
    """Maxfiy ma'lumot aniqlangan holat."""
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(index=True, foreign_key="agent.id")
    source: str                       # "event" yoki "file"
    ref_id: Optional[int] = None      # tegishli Event yoki CapturedFile id
    kinds: str                        # topilgan turlar: "card,keyword"
    snippet: Optional[str] = None     # niqoblangan namuna
    severity: str = Field(default="crit")
    occurred_at: datetime = Field(default_factory=utcnow, index=True)


class Screenshot(SQLModel, table=True):
    """Saqlangan ekran surati."""
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(index=True, foreign_key="agent.id")
    path: str
    app: Optional[str] = None
    title: Optional[str] = None
    occurred_at: datetime = Field(default_factory=utcnow, index=True)
    created_at: datetime = Field(default_factory=utcnow)
