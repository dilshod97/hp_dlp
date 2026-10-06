"""Agent sozlamasi — config.json dan o'qiladi, barqaror agent_uid saqlaydi.

PyInstaller bilan .exe qilinganda (frozen) config.json exe yonidan yoki
%PROGRAMDATA%\\HP-DLP dan o'qiladi; agent_uid ham o'sha yoziladigan joyда saqlanadi.
"""
import json
import os
import socket
import sys
import uuid
from dataclasses import dataclass, field


def _base_dir() -> str:
    """Kod yoki exe joylashgan papka."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _state_dir() -> str:
    """Yoziladigan holat papkasi (uid, config uchun).

    Frozen (.exe) bo'lsa — exe yonidagi papka (per-user o'rnatishда yoziladi;
    avtomatik yangilanish shu yerга yoza oladi). Aks holda PROGRAMDATA yoki base.
    """
    if getattr(sys, "frozen", False):
        return _base_dir()
    pd = os.environ.get("PROGRAMDATA")
    if pd:
        d = os.path.join(pd, "HP-DLP")
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except OSError:
            pass
    return _base_dir()


AGENT_DIR = _base_dir()
UID_FILE = os.path.join(_state_dir(), ".agent_uid")

# Kod ichiga joylangan standart sozlama — tashqi config.json topilmasa shu ishlatiladi
# (agent hech qachon "config topilmadi" xatosидан qulamaydi). Tashqi config bo'lsa — u ustun.
_DEFAULTS = {
    "server_url": "http://10.42.0.129:8001",
    "api_key": "dev-agent-key-change-me",
    "full_name": "",
    "poll_interval_sec": 5,
    "screenshot_interval_sec": 60,
    "enabled_collectors": [
        "active_window", "keyboard", "usb", "printer", "software",
        "clipboard", "file_monitor", "web", "telegram", "files", "screenshot",
    ],
}


@dataclass
class Config:
    server_url: str
    api_key: str
    full_name: str = ""
    poll_interval_sec: int = 5
    screenshot_interval_sec: int = 60
    enabled_collectors: list[str] = field(default_factory=lambda: ["active_window", "screenshot"])
    agent_uid: str = ""
    hostname: str = ""
    ip_address: str = ""


def _local_ip() -> str | None:
    """Kompyuterning asosiy lokal IP manzilini aniqlaydi."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # paket yubormaydi, faqat marshrutни aniqlaydi
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:  # noqa: BLE001
        return None


def _load_or_create_uid() -> str:
    """agent_uid bir marta yaratiladi va faylда saqlanadi (qayta ishga tushganda o'zgarmaydi)."""
    if os.path.exists(UID_FILE):
        with open(UID_FILE, "r", encoding="utf-8") as f:
            value = f.read().strip()
            if value:
                return value
    value = str(uuid.uuid4())
    with open(UID_FILE, "w", encoding="utf-8") as f:
        f.write(value)
    return value


def load_config(path: str | None = None) -> Config:
    """Sozlamani config.json dan o'qiydi. Environment o'zgaruvchilari ustun turadi.

    Docker/konteynerda config.json bo'lmasa, faqat env orqali ham ishlashi mumkin:
      HP_SERVER_URL, HP_API_KEY, HP_FULL_NAME, HP_COLLECTORS (vergul bilan),
      HP_POLL_INTERVAL_SEC, HP_SCREENSHOT_INTERVAL_SEC
    """
    # config.json ni topish: argumentdagi yo'l -> HP_CONFIG env -> exe yoni -> state dir
    candidates = [
        path,
        os.environ.get("HP_CONFIG"),
        os.path.join(AGENT_DIR, "config.json"),
        os.path.join(_state_dir(), "config.json"),
    ]
    # Oxirgi chora: exe ichiga joylangan standart config (yolg'iz exe ham ishlashi uchun)
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(getattr(sys, "_MEIPASS", AGENT_DIR), "config.example.json"))
    path = next((c for c in candidates if c and os.path.exists(c)), None)
    # Standart sozlama ustiga tashqi config qo'shiladi (tashqi qiymatlar ustun)
    data: dict = dict(_DEFAULTS)
    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception:  # noqa: BLE001 — buzuq config bo'lsa, standart bilan davom etamiz
            pass

    server_url = os.getenv("HP_SERVER_URL") or data.get("server_url")
    api_key = os.getenv("HP_API_KEY") or data.get("api_key")

    env_collectors = os.getenv("HP_COLLECTORS")
    collectors = (
        [c.strip() for c in env_collectors.split(",") if c.strip()]
        if env_collectors
        else data.get("enabled_collectors", _DEFAULTS["enabled_collectors"])
    )

    return Config(
        server_url=server_url.rstrip("/"),
        api_key=api_key,
        full_name=os.getenv("HP_FULL_NAME") or data.get("full_name", ""),
        poll_interval_sec=int(os.getenv("HP_POLL_INTERVAL_SEC") or data.get("poll_interval_sec", 5)),
        screenshot_interval_sec=int(os.getenv("HP_SCREENSHOT_INTERVAL_SEC") or data.get("screenshot_interval_sec", 60)),
        enabled_collectors=collectors,
        agent_uid=_load_or_create_uid(),
        hostname=socket.gethostname(),
        ip_address=_local_ip() or "",
    )
