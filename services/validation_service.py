"""Foydalanuvchi kiritgan ma'lumotlarni tekshirish va standartlashtirish.

Bu yerda hech qanday aniq ism, telefon yoki pasport qiymati yo'q:
faqat format qoidalari tekshiriladi.
"""
import re

# O'zbek lotin yozuvidagi apostrof variantlari: ' ‘ ’ ʻ ʼ ` ´ ′
APOSTROPHES = "'‘’ʻʼ`´′"
_APOSTROPHE_RE = re.compile(f"[{re.escape(APOSTROPHES)}]")

# Har bir so'z faqat lotin harflaridan iborat; so'z ichida apostrof bo'lishi mumkin
# (masalan, O'G'LI, MA'RUF). Kirill, raqam, emoji va boshqa belgilar o'tmaydi.
_NAME_WORD_RE = re.compile(r"^[A-Z]+(?:'[A-Z]+)*$")
NAME_MIN_WORDS = 2  # familiya + ism
NAME_MAX_WORDS = 4  # + otasining ismi va "O'G'LI"/"QIZI"

PHONE_LOCAL_RE = re.compile(r"^[0-9]{9}$")
PHONE_FULL_RE = re.compile(r"^998[0-9]{9}$")
PASSPORT_RE = re.compile(r"^[A-Z]{2}[0-9]{7}$")


# ---------------- F.I.Sh. ----------------

def normalize_full_name(value) -> str:
    """Apostroflarni bitta ko'rinishga keltiradi, bo'sh joylarni tozalaydi, katta harfga o'tkazadi."""
    text = _APOSTROPHE_RE.sub("'", str(value or ""))
    return " ".join(text.split()).upper()


def validate_name(value) -> str | None:
    """To'g'ri bo'lsa standart ko'rinishdagi F.I.Sh.ni, aks holda None qaytaradi."""
    name = normalize_full_name(value)
    words = name.split(" ")
    if not NAME_MIN_WORDS <= len(words) <= NAME_MAX_WORDS:
        return None
    for word in words:
        if len(word.replace("'", "")) < 2 or not _NAME_WORD_RE.match(word):
            return None
    return name


def display_name(name: str) -> str:
    """Standart F.I.Sh.ni chiroyli ko'rinishda chiqarish uchun (O'/G' -> O‘/G‘)."""
    return name.replace("'", "‘")


# ---------------- Telefon ----------------

def validate_phone(value) -> str | None:
    """Qo'lda kiritilgan raqam: faqat XXXXXXXXX yoki 998XXXXXXXXX.

    To'g'ri bo'lsa 998XXXXXXXXX ko'rinishida qaytaradi, aks holda None.
    """
    text = str(value or "").strip()
    if PHONE_LOCAL_RE.match(text):
        return "998" + text
    if PHONE_FULL_RE.match(text):
        return text
    return None


def normalize_phone(value) -> str | None:
    """Excel yoki Telegram Contact'dagi raqamni 998XXXXXXXXX ko'rinishiga keltiradi.

    Bu yerda +, bo'sh joy, chiziqcha kabi belgilar olib tashlanadi
    (qo'lda kiritilgan raqam uchun validate_phone ishlatiladi).
    """
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    if len(digits) == 9:
        digits = "998" + digits
    return digits if PHONE_FULL_RE.match(digits) else None


# ---------------- Pasport ----------------

def validate_passport(value) -> str | None:
    """Faqat 2 ta katta lotin harfi + 7 ta raqam (bo'sh joy, chiziqcha, kichik harfsiz)."""
    text = str(value or "").strip()
    return text if PASSPORT_RE.match(text) else None


def normalize_passport(value) -> str:
    """Excel'dagi pasportni solishtirish uchun: katta harf, bo'sh joy va belgilarsiz."""
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


# ---------------- Loglar uchun ----------------

def mask_value(value) -> str:
    """Maxfiy qiymatni loglarda ochiq ko'rsatmaslik uchun maskalaydi."""
    text = str(value or "")
    if len(text) <= 4:
        return "*" * len(text)
    return text[:2] + "*" * (len(text) - 4) + text[-2:]
