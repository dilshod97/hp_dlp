"""Skrinshot oluvchi — mss orqali, barcha platformalarda ishlaydi (Mac ham)."""
import io
import logging

from .base import ScreenshotProvider

log = logging.getLogger("agent.screenshot")


class MssScreenshot(ScreenshotProvider):
    name = "screenshot"

    def __init__(self, max_width: int = 1600, quality: int = 70):
        self.max_width = max_width
        self.quality = quality

    def capture(self) -> tuple[bytes, str, str] | None:
        try:
            import mss
            from PIL import Image
        except ImportError as e:
            log.error("mss/Pillow o'rnatilmagan: %s", e)
            return None

        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]  # barcha ekranlar birlashган
                raw = sct.grab(monitor)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

            if img.width > self.max_width:
                ratio = self.max_width / img.width
                img = img.resize((self.max_width, int(img.height * ratio)))

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=self.quality)
            return buf.getvalue(), "", ""
        except Exception as e:  # noqa: BLE001
            log.warning("skrinshot olinmadi: %s", e)
            return None
