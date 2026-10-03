"""Tayyor savol-javoblar bazasi (faq.txt) bo'yicha javob qidirish.

Bot javobni o'zi o'ylab topmaydi: faqat faylda yozilgan javoblardan birini qaytaradi.

Fayl formati:

    ## Mavzu nomi (tugmada ko'rinadi)
    Kalit so'zlar: parol, unutdim, tiklash
    Javob matni (bir yoki bir necha qator).

'#' bilan boshlanib, '##' bo'lmagan qatorlar izoh hisoblanadi.
"""
import logging
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from services.validation_service import APOSTROPHES

logger = logging.getLogger(__name__)

# Kirill yozuvida yozilgan savollarni ham tushunish uchun
_CYRILLIC_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "s",
    "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "'", "ы": "i", "ь": "", "э": "e", "ю": "yu",
    "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h",
}
_APOSTROPHE_RE = re.compile(f"[{re.escape(APOSTROPHES)}]")


def normalize_text(text: str) -> str:
    """Kichik harf, kirill -> lotin, apostroflarni birxillashtirish, faqat harf/raqam/bo'sh joy."""
    text = str(text or "").lower()
    text = "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)
    text = _APOSTROPHE_RE.sub("'", text)
    # O'zbek lotin yozuvida apostrof so'z ichida qoladi (o'qish, g'oya), qolgan belgilar bo'sh joy
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return " ".join(w.strip("'") for w in text.split() if w.strip("'"))


@dataclass(frozen=True)
class FaqEntry:
    title: str
    keywords: tuple[str, ...]  # normalizatsiya qilingan kalit so'zlar/iboralar
    answer: str


def parse_faq(text: str) -> list[FaqEntry]:
    entries: list[FaqEntry] = []
    title, keywords, answer_lines = None, (), []

    def flush():
        if title and answer_lines:
            answer = "\n".join(answer_lines).strip()
            if answer:
                entries.append(FaqEntry(title, keywords, answer))

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            flush()
            title, keywords, answer_lines = line[3:].strip(), (), []
        elif line.startswith("#"):
            continue
        elif title is None:
            continue
        elif normalize_text(line.split(":", 1)[0]) == "kalit so'zlar" and ":" in line and not keywords:
            parts = line.split(":", 1)[1].split(",")
            keywords = tuple(k for k in (normalize_text(p) for p in parts) if k)
        else:
            answer_lines.append(line)
    flush()
    return entries


def _keyword_matches(keyword: str, words: list[str]) -> bool:
    """Kalit so'zning har bir so'zi savoldagi ketma-ket so'zlarning boshiga mos kelishi kerak.

    Masalan: "parol" -> "parolim"; "parolni unut" -> "parolimni unutdim" emas, lekin
    "parolni unutib" ga mos keladi.
    """
    parts = keyword.split()
    for i in range(len(words) - len(parts) + 1):
        if all(words[i + j].startswith(part) for j, part in enumerate(parts)):
            return True
    return False


def find_answer(entries: list[FaqEntry], question: str) -> FaqEntry | None:
    """Eng ko'p ball to'plagan javobni qaytaradi; hech biri mos kelmasa None.

    Ball teng bo'lsa, faylda yuqoriroqda turgan mavzu tanlanadi.
    """
    text = normalize_text(question)
    if not text:
        return None
    words = text.split()
    best, best_score = None, 0
    for entry in entries:
        # Ko'p so'zli ibora aniqroq bo'lgani uchun har bir so'zi uchun 1 ball oladi
        score = sum(len(kw.split()) for kw in entry.keywords if _keyword_matches(kw, words))
        if score > best_score:
            best, best_score = entry, score
    return best


class FaqBase:
    """faq.txt ni xotirada saqlaydi; fayl o'zgarsa avtomatik qayta o'qiydi."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._mtime = None
        self._entries: list[FaqEntry] = []
        self._missing_logged = False

    def entries(self) -> list[FaqEntry]:
        with self._lock:
            try:
                mtime = os.path.getmtime(self.path)
            except OSError:
                if not self._missing_logged:
                    logger.warning("Savol-javob fayli topilmadi: %s", self.path.name)
                    self._missing_logged = True
                self._mtime = None
                self._entries = []
                return self._entries
            self._missing_logged = False
            if mtime != self._mtime:
                self._entries = parse_faq(self.path.read_text(encoding="utf-8"))
                self._mtime = mtime
                logger.info("Savol-javob bazasi yuklandi: %d ta mavzu", len(self._entries))
            return self._entries

    def find(self, question: str) -> FaqEntry | None:
        return find_answer(self.entries(), question)
