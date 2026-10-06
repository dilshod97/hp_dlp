"""Kolektor interfeysi — hamma ma'lumot yig'uvchilar shundan meros oladi."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Collector(ABC):
    name: str = "base"

    @abstractmethod
    def poll(self) -> list[dict]:
        """Har davrda chaqiriladi. Yangi hodisalar ro'yxatini qaytaradi (bo'sh bo'lishi mumkin).

        Hodisa formati EventIn sxemasiga mos bo'lishi kerak:
        {type, channel?, severity, app?, title?, text?, details?, occurred_at?}
        """
        raise NotImplementedError


class ScreenshotProvider(ABC):
    """Skrinshot oluvchilar alohida interfeys — tsiklda boshqacha ishlatiladi."""
    name: str = "screenshot"

    @abstractmethod
    def capture(self) -> tuple[bytes, str, str] | None:
        """(jpeg_bytes, app, title) yoki None qaytaradi."""
        raise NotImplementedError


class FileProvider(ABC):
    """Ushlangan fayllarni beruvchilar interfeysi."""
    name: str = "files"

    @abstractmethod
    def capture(self) -> dict | None:
        """Lug'at qaytaradi yoki None. Kalitlar:
        data(bytes), filename, mime, channel, source_path,
        source_url (ixtiyoriy), context_app (ixtiyoriy), context_title (ixtiyoriy).
        """
        raise NotImplementedError
