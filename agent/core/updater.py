"""Agentni avtomatik yangilash.

Serverdan eng yangi versiyani so'raydi; yangiroq bo'lsa, exe'ni yuklab,
SHA256 ni tekshirib, o'zini almashtiradi va qayta ishga tushadi.

Faqat PyInstaller bilan .exe qilingan Windows agentda haqiqiy almashtirish bo'ladi.
Boshqa holatda (dev/mock) faqat "yangilanish bor" deb log yoziladi.
"""
import hashlib
import logging
import os
import subprocess
import sys

log = logging.getLogger("agent.updater")

IS_FROZEN = getattr(sys, "frozen", False)
IS_WINDOWS = sys.platform.startswith("win")


def _ver_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:  # noqa: BLE001
        return (0,)


def cleanup_old() -> None:
    """Oldingi yangilanishdan qolgan .old faylni o'chiradi."""
    if not IS_FROZEN:
        return
    old = sys.executable + ".old"
    try:
        if os.path.exists(old):
            os.remove(old)
    except OSError:
        pass


def check_and_update(client, current_version: str) -> bool:
    """Yangilanish bo'lsa bajaradi. True qaytarsa — jarayon qayta ishga tushirilmoqda."""
    info = client.get_latest_version()
    if not info or not info.get("version"):
        return False
    latest = info["version"]
    if _ver_tuple(latest) <= _ver_tuple(current_version):
        return False

    log.info("Yangi versiya mavjud: %s (joriy %s)", latest, current_version)
    data = client.download_update(info.get("url", ""))
    if not data:
        return False

    # Butunlikni tekshirish
    expected = (info.get("sha256") or "").lower()
    actual = hashlib.sha256(data).hexdigest()
    if expected and actual != expected:
        log.error("SHA256 mos kelmadi — yangilanish bekor qilindi")
        return False

    if not (IS_FROZEN and IS_WINDOWS):
        log.info("Yangilanish yuklandi va tekshirildi, lekin bu muhit (dev/mock) "
                 "o'zini almashtira olmaydi. Haqiqiy Windows exe'da almashadi.")
        return False

    exe = sys.executable
    new, old = exe + ".new", exe + ".old"
    try:
        with open(new, "wb") as f:
            f.write(data)
        if os.path.exists(old):
            os.remove(old)
        os.rename(exe, old)      # ishlab turgan exe'ni nomlash mumkin
        os.rename(new, exe)      # yangisini joyiga qo'yish
        log.info("Yangilandi -> %s. Qayta ishga tushmoqda.", latest)
        subprocess.Popen([exe])  # yangi versiyani ishga tushirish
        return True
    except Exception as e:  # noqa: BLE001
        log.error("Almashtirishda xato: %s", e)
        # orqaga qaytarish
        try:
            if not os.path.exists(exe) and os.path.exists(old):
                os.rename(old, exe)
        except OSError:
            pass
        return False
