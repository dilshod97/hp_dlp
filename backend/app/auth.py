"""Autentifikatsiya.

- Agentlar: X-API-Key sarlavhasi (umumiy kalit).
- Panel (admin): foydalanuvchi/parol -> imzolangan token (Authorization: Bearer).

Parollar pbkdf2 (stdlib) bilan hash qilinadi. Token hmac bilan imzolanadi —
qo'shimcha kutubxona kerak emas. Keyingi bosqichda rollar bo'yicha ruxsatlar kengaytiriladi.
"""
import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import Header, HTTPException, status

from .config import settings

TOKEN_TTL = 12 * 3600  # 12 soat


# ---------- Parol ----------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:  # noqa: BLE001
        return False


# ---------- Token ----------
def _sign(data: bytes) -> str:
    sig = hmac.new(settings.secret_key.encode(), data, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def make_token(username: str, role: str) -> str:
    payload = {"u": username, "r": role, "exp": int(time.time()) + TOKEN_TTL}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{body}.{_sign(body.encode())}"


def parse_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".", 1)
        if not hmac.compare_digest(sig, _sign(body.encode())):
            return None
        pad = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(body + pad))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:  # noqa: BLE001
        return None


# ---------- Dependencies ----------
def require_agent_key(x_api_key: str = Header(default="")) -> None:
    if x_api_key != settings.agent_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Noto'g'ri yoki yo'q agent kaliti")


def require_dashboard(authorization: str = Header(default="")) -> dict:
    prefix = "Bearer "
    token = authorization[len(prefix):] if authorization.startswith(prefix) else ""
    payload = parse_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Kirish talab qilinadi yoki token muddati tugagan")
    return payload


def require_role(*roles: str):
    """Faqat berilgan rollarga ruxsat beruvchi dependency. superadmin hamma joyga kiradi."""
    def dep(authorization: str = Header(default="")) -> dict:
        payload = require_dashboard(authorization)
        role = payload.get("r")
        if role != "superadmin" and role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Bu amal uchun ruxsat yo'q")
        return payload
    return dep
