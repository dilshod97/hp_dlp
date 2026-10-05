"""Maxfiy ma'lumotni aniqlash — regex va kalit so'zlar.

Topilgan qiymatlar to'liq saqlanmaydi (niqoblanadi) — maxfiylik uchun.
"""
import re

CARD_RE = re.compile(r"(?:\d[ -]?){13,19}")
# O'zbekiston pasport seriyasi: 2 harf + 7 raqam (masalan AA1234567)
PASSPORT_RE = re.compile(r"\b[A-Z]{2}\s?\d{7}\b")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _mask_card(digits: str) -> str:
    return f"**** **** **** {digits[-4:]}"


def scan_text(text: str, keywords: list[str], detect_cards: bool = True, detect_passport: bool = True) -> list[dict]:
    """Matndan maxfiy ma'lumotlarni qidiradi. [{kind, sample}] qaytaradi."""
    if not text:
        return []
    found: list[dict] = []

    if detect_cards:
        for m in CARD_RE.finditer(text):
            digits = re.sub(r"\D", "", m.group())
            if 13 <= len(digits) <= 19 and _luhn_ok(digits):
                found.append({"kind": "card", "sample": _mask_card(digits)})

    if detect_passport:
        for m in PASSPORT_RE.finditer(text):
            s = m.group().strip()
            found.append({"kind": "passport", "sample": s[:2] + "*****" + s[-2:]})

    low = text.lower()
    for kw in keywords:
        kw = kw.strip()
        if kw and kw.lower() in low:
            found.append({"kind": "keyword", "sample": kw})

    # takrorlanmas
    seen, uniq = set(), []
    for f in found:
        key = (f["kind"], f["sample"])
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return uniq
