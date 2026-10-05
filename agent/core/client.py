"""Server bilan aloqa. Xato bo'lsa hodisalarni navbatda saqlaydi va qayta yuboradi."""
import collections
import logging

import requests

log = logging.getLogger("agent.client")


class ServerClient:
    def __init__(self, server_url: str, api_key: str, agent_uid: str, max_queue: int = 5000):
        self.base = server_url
        self.agent_uid = agent_uid
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
        # Server o'chiq bo'lsa, hodisalar shu navbatda to'planadi.
        self.queue: collections.deque = collections.deque(maxlen=max_queue)

    def hello(self, hostname: str, full_name: str, os_name: str,
              ip_address: str | None = None, agent_version: str | None = None) -> bool:
        try:
            r = self.session.post(
                f"{self.base}/api/v1/ingest/hello",
                json={
                    "agent_uid": self.agent_uid, "hostname": hostname,
                    "full_name": full_name, "os_name": os_name, "ip_address": ip_address,
                    "agent_version": agent_version,
                },
                timeout=10,
            )
            r.raise_for_status()
            log.info("Serverga ulanish muvaffaqiyatli: %s", r.json())
            return True
        except requests.RequestException as e:
            log.warning("hello xatosi: %s", e)
            return False

    def get_latest_version(self) -> dict | None:
        try:
            r = self.session.get(f"{self.base}/api/v1/agent/version", timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            log.debug("versiya so'rovida xato: %s", e)
            return None

    def download_update(self, url: str) -> bytes | None:
        try:
            full = url if url.startswith("http") else f"{self.base}{url}"
            r = self.session.get(full, timeout=120)
            r.raise_for_status()
            return r.content
        except requests.RequestException as e:
            log.warning("yangilanishni yuklab bo'lmadi: %s", e)
            return None

    def send_events(self, events: list[dict]) -> None:
        """Yangi hodisalarni navbatga qo'shib, butun navbatni yuborishga urinadi."""
        self.queue.extend(events)
        if not self.queue:
            return
        batch = list(self.queue)
        try:
            r = self.session.post(
                f"{self.base}/api/v1/ingest/events",
                json={"agent_uid": self.agent_uid, "events": batch},
                timeout=15,
            )
            r.raise_for_status()
            self.queue.clear()
            log.info("%d ta hodisa yuborildi", len(batch))
        except requests.RequestException as e:
            log.warning("events yuborilmadi (navbatda %d ta kutmoqda): %s", len(self.queue), e)

    def send_file(self, data: bytes, filename: str, mime: str = "application/octet-stream",
                  channel: str = "", source_path: str = "") -> None:
        try:
            r = self.session.post(
                f"{self.base}/api/v1/ingest/file",
                data={"agent_uid": self.agent_uid, "filename": filename, "channel": channel,
                      "source_path": source_path},
                files={"file": (filename, data, mime)},
                timeout=30,
            )
            r.raise_for_status()
            log.info("Fayl yuborildi: %s", r.json())
        except requests.RequestException as e:
            log.warning("fayl yuborilmadi: %s", e)

    def send_screenshot(self, jpeg_bytes: bytes, app: str = "", title: str = "") -> None:
        try:
            r = self.session.post(
                f"{self.base}/api/v1/ingest/screenshot",
                data={"agent_uid": self.agent_uid, "app": app, "title": title},
                files={"file": ("shot.jpg", jpeg_bytes, "image/jpeg")},
                timeout=20,
            )
            r.raise_for_status()
            log.info("Skrinshot yuborildi: %s", r.json())
        except requests.RequestException as e:
            log.warning("skrinshot yuborilmadi: %s", e)
