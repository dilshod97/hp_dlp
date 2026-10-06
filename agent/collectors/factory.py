"""Platformaga qarab to'g'ri kolektorlarni tanlaydi.

Windows'da  -> haqiqiy Windows kolektorlari
Boshqa OT'da -> mock (soxta) kolektorlar — Mac/Docker'da sinash uchun

Skrinshot har ikkala holatda ham mss orqali (cross-platform) ishlaydi.
"""
import logging
import platform

from .base import Collector, ScreenshotProvider, FileProvider
from .screenshot import MssScreenshot

log = logging.getLogger("agent.factory")

IS_WINDOWS = platform.system() == "Windows"

# Qo'llab-quvvatlanadigan kolektor nomlari.
_COLLECTOR_NAMES = [
    "active_window", "keyboard", "usb", "printer", "software",
    "clipboard", "file_monitor", "web", "telegram", "email",
]


def _make(name: str) -> Collector | None:
    if IS_WINDOWS:
        from . import windows as w
        mapping = {
            "active_window": w.WindowsActiveWindow,
            "keyboard": w.WindowsKeyboard,
            "usb": w.WindowsUsb,
            "printer": w.WindowsPrinter,
            "software": w.WindowsSoftware,
            "clipboard": w.WindowsClipboard,
            "file_monitor": w.WindowsFileMonitor,
            "web": w.WindowsWeb,
            "telegram": w.WindowsTelegram,   # Desktop, UIAutomation (best-effort)
            # email — xodimlar webmail (Chrome) ishlatadi, veb nazorati qamrab oladi
        }
    else:
        from . import mock as m
        mapping = {
            "active_window": m.MockActiveWindow,
            "keyboard": m.MockKeyboard,
            "usb": m.MockUsb,
            "printer": m.MockPrinter,
            "software": m.MockSoftware,
            "clipboard": m.MockClipboard,
            "file_monitor": m.MockFileMonitor,
            "web": m.MockWeb,
            "telegram": m.MockTelegram,
            "email": m.MockEmail,
        }
    cls = mapping.get(name)
    return cls() if cls else None


def build_collectors(enabled: list[str]) -> tuple[list[Collector], ScreenshotProvider | None, list[FileProvider]]:
    collectors: list[Collector] = []
    for name in enabled:
        if name in _COLLECTOR_NAMES:
            inst = _make(name)
            if inst:
                collectors.append(inst)

    screenshot = MssScreenshot() if "screenshot" in enabled else None

    # Fayl provayderlari: papka/USB kuzatuvi + clipboard orqali nusxalangan fayl/rasm.
    # Ikkisi ham send_file orqali yuboradi, shuning uchun "files" bilan birga yoqiladi.
    file_providers: list[FileProvider] = []
    if "files" in enabled:
        if IS_WINDOWS:
            from .windows import WindowsFiles, WindowsClipboardFiles
            file_providers.append(WindowsFiles())
            file_providers.append(WindowsClipboardFiles())
        else:
            from .mock import MockFiles, MockClipboardFiles
            file_providers.append(MockFiles())
            file_providers.append(MockClipboardFiles())

    if not IS_WINDOWS and collectors:
        log.info("Windows emas — kolektorlar uchun MOCK ishlatilmoqda")
    log.info("Faollashtirilgan kolektorlar: %s + skrinshot=%s + fayl provayderlar=%s",
             [c.name for c in collectors], screenshot is not None,
             [p.name for p in file_providers])
    return collectors, screenshot, file_providers
