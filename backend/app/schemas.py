"""API uchun kirish/chiqish sxemalari (Pydantic)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HelloIn(BaseModel):
    agent_uid: str
    hostname: str
    full_name: Optional[str] = None
    ip_address: Optional[str] = None
    os_name: Optional[str] = None
    agent_version: Optional[str] = None


class HelloOut(BaseModel):
    agent_id: int
    # Keyinchalik: agentga yuboriladigan sozlama/siyosat shu yerda qaytadi.
    screenshot_interval_sec: int = 60
    enabled_collectors: list[str] = ["active_window", "keyboard", "usb", "printer", "software", "screenshot"]


class EventIn(BaseModel):
    type: str
    channel: Optional[str] = None
    severity: str = "info"
    app: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    details: dict = Field(default_factory=dict)
    occurred_at: Optional[datetime] = None


class EventsBatchIn(BaseModel):
    agent_uid: str
    events: list[EventIn]


class EventOut(BaseModel):
    id: int
    agent_id: int
    type: str
    channel: Optional[str]
    severity: str
    app: Optional[str]
    title: Optional[str]
    text: Optional[str]
    details: dict = Field(default_factory=dict)
    occurred_at: datetime


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    token: str
    username: str
    role: str


class AgentUpdate(BaseModel):
    display_name: Optional[str] = None
    note: Optional[str] = None
    active: Optional[bool] = None


class FileOut(BaseModel):
    id: int
    agent_id: int
    filename: str
    url: str
    source_path: Optional[str] = None
    source_url: Optional[str] = None
    context_app: Optional[str] = None
    context_title: Optional[str] = None
    size: int
    mime: Optional[str]
    channel: Optional[str]
    severity: str
    occurred_at: datetime


class ScreenshotOut(BaseModel):
    id: int
    agent_id: int
    url: str
    app: Optional[str]
    title: Optional[str]
    occurred_at: datetime


class AgentOut(BaseModel):
    id: int
    hostname: str
    full_name: Optional[str]
    display_name: Optional[str]
    note: Optional[str]
    active: bool
    ip_address: Optional[str]
    os_name: Optional[str]
    agent_version: Optional[str]
    last_seen: datetime


class VersionOut(BaseModel):
    version: Optional[str] = None
    sha256: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class ReleaseOut(BaseModel):
    id: int
    version: str
    filename: str
    sha256: str
    notes: Optional[str]
    created_at: datetime


class OverviewOut(BaseModel):
    agents_total: int
    agents_online: int
    events_today: int
    alerts_today: int
    detections_today: int = 0


class DetectionOut(BaseModel):
    id: int
    agent_id: int
    source: str
    ref_id: Optional[int]
    kinds: str
    snippet: Optional[str]
    severity: str
    occurred_at: datetime


class PolicyOut(BaseModel):
    keywords: str
    detect_cards: bool
    detect_passport: bool
    block_usb: bool
    retention_days: int


class PolicyUpdate(BaseModel):
    keywords: Optional[str] = None
    detect_cards: Optional[bool] = None
    detect_passport: Optional[bool] = None
    block_usb: Optional[bool] = None
    retention_days: Optional[int] = None


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"


class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None


class AuditOut(BaseModel):
    id: int
    actor: str
    action: str
    target: Optional[str]
    created_at: datetime
