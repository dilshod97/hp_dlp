"""Agentning asosiy tsikli: kolektorlardan yig'ib, serverga yuboradi."""
import logging
import platform
import time

from core.config import load_config
from core.client import ServerClient
from core.version import VERSION
from core import updater
from collectors.factory import build_collectors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("agent")


def main() -> None:
    cfg = load_config()
    log.info("Agent ishga tushdi. v%s uid=%s host=%s os=%s",
             VERSION, cfg.agent_uid[:8], cfg.hostname, platform.system())

    updater.cleanup_old()  # oldingi yangilanish qoldig'ini tozalash

    client = ServerClient(cfg.server_url, cfg.api_key, cfg.agent_uid)
    os_name = f"{platform.system()} {platform.release()}"

    def do_hello() -> bool:
        return client.hello(cfg.hostname, cfg.full_name, os_name, agent_version=VERSION)

    registered = do_hello()

    # Ishga tushganda yangilanishni tekshirish
    if registered and updater.check_and_update(client, VERSION):
        return  # qayta ishga tushmoqda

    collectors, screenshot, file_provider = build_collectors(cfg.enabled_collectors)

    last_screenshot = 0.0
    last_file = 0.0
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

            # 2) Skrinshot (o'z davrida)
            now = time.time()
            if screenshot and now - last_screenshot >= cfg.screenshot_interval_sec:
                shot = screenshot.capture()
                if shot:
                    data, app, title = shot
                    client.send_screenshot(data, app, title)
                last_screenshot = now

            # 2b) Ushlangan fayl (o'z davrida)
            if registered and file_provider and now - last_file >= cfg.screenshot_interval_sec:
                f = file_provider.capture()
                if f:
                    fdata, fname, mime, channel, src = f
                    client.send_file(fdata, fname, mime, channel, src)
                last_file = now

            # 3) Vaqti-vaqti bilan "men tirikman" (har 60s)
            if now - last_hello >= 60:
                client.hello(cfg.hostname, cfg.full_name, os_name, agent_version=VERSION)
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
    main()
