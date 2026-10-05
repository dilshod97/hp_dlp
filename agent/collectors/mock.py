"""Mac/rivojlantirish uchun soxta kolektorlar — Windows bo'lmagan joyda ishlatiladi.

Butun quvurni (agent → server → panel) Windows'siz sinab ko'rish imkonini beradi.
Har bir soxta kolektor haqiqiy kolektor bilan bir xil hodisa formatini qaytaradi.
"""
import random
import time

from .base import Collector, FileProvider, now_iso

_APPS = [
    ("chrome.exe", "Yangiliklar — Google Chrome"),
    ("Telegram.exe", "Ish guruhi — Telegram"),
    ("Code.exe", "main.py — Visual Studio Code"),
    ("EXCEL.EXE", "hisobot_2026.xlsx — Excel"),
    ("OUTLOOK.EXE", "Kiruvchi xatlar — Outlook"),
]


class MockActiveWindow(Collector):
    """Faol oyna almashganda, tark etilgan oynada sarflangan vaqtni (duration_sec) qaytaradi."""
    name = "active_window"

    def __init__(self):
        self._cur = None
        self._since = time.time()

    def poll(self) -> list[dict]:
        app, title = random.choice(_APPS)
        if self._cur is None:
            self._cur = (app, title)
            self._since = time.time()
            return []
        if (app, title) == self._cur:
            return []
        prev_app, prev_title = self._cur
        duration = int(time.time() - self._since)
        self._cur = (app, title)
        self._since = time.time()
        return [{
            "type": "active_window", "severity": "info",
            "app": prev_app, "title": prev_title,
            "occurred_at": now_iso(),
            "details": {"duration_sec": duration, "source": "mock"},
        }]


class MockKeyboard(Collector):
    """Vaqti-vaqti bilan soxta terilgan matnni qaytaradi."""
    name = "keyboard"
    _SAMPLES = [
        "assalomu alaykum hisobotni yubordim",
        "narxlarni tekshirib ko'ring",
        "ertaga yig'ilish soat 10 da",
        "shartnoma tayyor rahmat",
    ]

    def __init__(self):
        self._next = time.time() + random.randint(8, 15)

    def poll(self) -> list[dict]:
        if time.time() < self._next:
            return []
        self._next = time.time() + random.randint(8, 15)
        app, title = random.choice(_APPS)
        return [{
            "type": "keyboard", "severity": "info",
            "app": app, "title": title,
            "text": random.choice(self._SAMPLES),
            "occurred_at": now_iso(),
            "details": {"source": "mock"},
        }]


class MockUsb(Collector):
    """Vaqti-vaqti bilan USB ulanish/uzilish hodisasini qaytaradi."""
    name = "usb"
    _DEVICES = [("E:", "Kingston 32GB"), ("F:", "SanDisk 64GB"), ("G:", "Transcend 16GB")]

    def __init__(self):
        self._next = time.time() + random.randint(12, 20)
        self._connected = None

    def poll(self) -> list[dict]:
        if time.time() < self._next:
            return []
        self._next = time.time() + random.randint(12, 20)
        if self._connected is None:
            drive, label = random.choice(self._DEVICES)
            self._connected = (drive, label)
            return [{
                "type": "usb", "channel": "usb", "severity": "warn",
                "title": f"USB disk ulandi: {drive} ({label})",
                "occurred_at": now_iso(),
                "details": {"action": "connected", "drive": drive, "label": label, "source": "mock"},
            }]
        drive, label = self._connected
        self._connected = None
        return [{
            "type": "usb", "channel": "usb", "severity": "info",
            "title": f"USB disk uzildi: {drive} ({label})",
            "occurred_at": now_iso(),
            "details": {"action": "disconnected", "drive": drive, "label": label, "source": "mock"},
        }]


class MockPrinter(Collector):
    """Vaqti-vaqti bilan soxta chop etish hodisasini qaytaradi."""
    name = "printer"
    _DOCS = [("hisobot.docx", 12), ("shartnoma.pdf", 4), ("hujjat.xlsx", 2)]

    def __init__(self):
        self._next = time.time() + random.randint(15, 25)

    def poll(self) -> list[dict]:
        if time.time() < self._next:
            return []
        self._next = time.time() + random.randint(15, 25)
        doc, pages = random.choice(self._DOCS)
        return [{
            "type": "print", "channel": "print", "severity": "info",
            "title": f"Hujjat chop etildi: {doc} ({pages} bet)",
            "occurred_at": now_iso(),
            "details": {"document": doc, "pages": pages, "printer": "HP LaserJet", "source": "mock"},
        }]


class MockSoftware(Collector):
    """Bir marta (biroz kechikib) soxta "yangi dastur o'rnatildi" hodisasini qaytaradi."""
    name = "software"

    def __init__(self):
        self._next = time.time() + random.randint(20, 30)
        self._done = False

    def poll(self) -> list[dict]:
        if self._done or time.time() < self._next:
            return []
        self._done = True
        return [{
            "type": "software", "severity": "warn",
            "title": "Yangi dastur o'rnatildi: AnyDesk 7.1",
            "occurred_at": now_iso(),
            "details": {"action": "installed", "name": "AnyDesk", "version": "7.1", "source": "mock"},
        }]


class MockFiles(FileProvider):
    """Vaqti-vaqti bilan soxta "ushlangan fayl" (matnli hujjat) qaytaradi."""
    name = "files"
    _FILES = [
        ("maxfiy_hisobot.txt", "usb",
         "MAXFIY\nQ3 moliyaviy hisobot\nDaromad: 1 250 000 000 so'm\nXarajat: 980 000 000 so'm"),
        ("mijozlar.csv", "telegram",
         "ism,telefon,shahar\nAli,+99890xxxxxxx,Toshkent\nVali,+99891xxxxxxx,Samarqand"),
        ("shartnoma_qoralama.txt", "email",
         "SHARTNOMA LOYIHASI\nTomonlar: A korxonasi va B MChJ\nSumma: kelishilган holda"),
    ]

    def __init__(self, interval_sec: int = 30):
        self.interval_sec = interval_sec
        self._next = time.time() + interval_sec

    def capture(self):
        if time.time() < self._next:
            return None
        self._next = time.time() + self.interval_sec
        name, channel, body = random.choice(self._FILES)
        folders = ["C:/Users/user/Downloads", "C:/Users/user/Documents", "D:/ish"]
        source_path = f"{random.choice(folders)}/{name}"
        return body.encode("utf-8"), name, "text/plain", channel, source_path


class MockClipboard(Collector):
    """Vaqti-vaqti bilan soxta clipboard (nusxa olingan matn) qaytaradi."""
    name = "clipboard"
    _SAMPLES = [
        "4111 1111 1111 1111",
        "parol: Qwerty123!",
        "mijoz ro'yxati: Ali, Vali, Hasan",
        "https://docs.google.com/spreadsheets/maxfiy",
    ]

    def __init__(self):
        self._next = time.time() + random.randint(14, 22)

    def poll(self) -> list[dict]:
        if time.time() < self._next:
            return []
        self._next = time.time() + random.randint(14, 22)
        app, _ = random.choice(_APPS)
        return [{
            "type": "clipboard", "channel": "clipboard", "severity": "info",
            "app": app, "text": random.choice(self._SAMPLES),
            "occurred_at": now_iso(), "details": {"source": "mock"},
        }]


class MockFileMonitor(Collector):
    """Vaqti-vaqti bilan soxta fayl harakati (yaratildi/o'zgardi/o'chdi) qaytaradi."""
    name = "file_monitor"
    _ACTS = [
        ("created", "yaratildi"), ("modified", "o'zgartirildi"),
        ("deleted", "o'chirildi"), ("moved", "ko'chirildi"),
    ]
    _FILES = ["hisobot.xlsx", "shartnoma.docx", "rasm.png", "mijozlar.csv", "backup.zip"]

    def __init__(self):
        self._next = time.time() + random.randint(10, 18)

    def poll(self) -> list[dict]:
        if time.time() < self._next:
            return []
        self._next = time.time() + random.randint(10, 18)
        action, uz = random.choice(self._ACTS)
        fname = random.choice(self._FILES)
        sev = "warn" if action in ("deleted", "moved") else "info"
        return [{
            "type": "file_monitor", "channel": "file", "severity": sev,
            "title": f"Fayl {uz}: {fname}",
            "occurred_at": now_iso(),
            "details": {"action": action, "path": f"C:/Users/user/Documents/{fname}", "source": "mock"},
        }]


class MockWeb(Collector):
    """Vaqti-vaqti bilan soxta tashrif buyurilgan sayt qaytaradi."""
    name = "web"
    _SITES = ["youtube.com", "facebook.com", "gmail.com", "telegram.org", "github.com", "olx.uz"]

    def __init__(self):
        self._next = time.time() + random.randint(7, 13)

    def poll(self) -> list[dict]:
        if time.time() < self._next:
            return []
        self._next = time.time() + random.randint(7, 13)
        site = random.choice(self._SITES)
        return [{
            "type": "web", "channel": "web", "severity": "info",
            "app": "chrome.exe", "title": site,
            "occurred_at": now_iso(),
            "details": {"url": f"https://{site}/", "duration_sec": random.randint(20, 600), "source": "mock"},
        }]


class MockTelegram(Collector):
    """Soxta Telegram yozishmasi (demo)."""
    name = "telegram"
    _MSGS = ["shartnoma faylini yubor", "pora masalasi hal bo'ldi", "ertaga uchrashamiz", "hisobotni tashla"]

    def __init__(self):
        self._next = time.time() + random.randint(16, 24)

    def poll(self) -> list[dict]:
        if time.time() < self._next:
            return []
        self._next = time.time() + random.randint(16, 24)
        return [{
            "type": "telegram", "channel": "telegram", "severity": "info",
            "app": "Telegram.exe", "text": random.choice(self._MSGS),
            "occurred_at": now_iso(), "details": {"source": "mock"},
        }]


class MockEmail(Collector):
    """Soxta e-mail (demo)."""
    name = "email"
    _MSGS = ["Mavzu: To'lov hujjatlari", "Mavzu: Maxfiy shartnoma", "Mavzu: Oylik hisobot"]

    def __init__(self):
        self._next = time.time() + random.randint(18, 26)

    def poll(self) -> list[dict]:
        if time.time() < self._next:
            return []
        self._next = time.time() + random.randint(18, 26)
        return [{
            "type": "email", "channel": "email", "severity": "info",
            "app": "OUTLOOK.EXE", "text": random.choice(self._MSGS),
            "occurred_at": now_iso(), "details": {"source": "mock"},
        }]
