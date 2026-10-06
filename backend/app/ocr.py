"""Rasm ichidagi matnni o'qish (OCR) — tesseract + pytesseract.

Maqsad: clipboard orqali nusxalangan rasm, yuklab olingan rasm va skrinshot
ichidagi matnни (pasport, karta, kalit so'zlar) o'qib, DLP skaniga berish.

tesseract o'rnatilmagan bo'lsa — bo'sh matn qaytaradi, xato bermaydi
(backend OCR'siz ham ishlayveradi).
"""
import io
import logging

log = logging.getLogger("ocr")

# O'rnatilган traineddata'ga qarab tillar. uzb+rus+eng — bizning hujjatlar shu tillarда.
_LANGS = "uzb+rus+eng"

_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif")

_available: bool | None = None   # tesseract bor-yo'qligi (bir marta tekshiriladi)


def _check() -> bool:
    global _available
    if _available is not None:
        return _available
    try:
        import pytesseract
        from PIL import Image  # noqa: F401
        pytesseract.get_tesseract_version()
        _available = True
        log.info("OCR tayyor (tesseract topildi)")
    except Exception as e:  # noqa: BLE001
        _available = False
        log.warning("OCR o'chirilган — tesseract topilmadi: %s", e)
    return _available


def is_image(mime: str | None, filename: str | None) -> bool:
    """Fayl rasm formatidami (mime yoki kengaytmaga qarab)."""
    if mime and mime.startswith("image/"):
        return True
    return (filename or "").lower().endswith(_IMAGE_EXT)


def extract_text(data: bytes, lang: str = _LANGS) -> str:
    """Rasm baytlaridan matn ajratadi. OCR yo'q yoki xato bo'lsa — bo'sh satr."""
    if not data or not _check():
        return ""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        try:
            text = pytesseract.image_to_string(img, lang=lang)
        except pytesseract.TesseractError:
            # kerakli til traineddata'si yo'q bo'lsa — standart (eng) bilan urinib ko'ramiz
            text = pytesseract.image_to_string(img)
        return (text or "").strip()
    except Exception as e:  # noqa: BLE001
        log.debug("OCR xato: %s", e)
        return ""
