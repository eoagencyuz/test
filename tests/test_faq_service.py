import os
import time

from services.faq_service import FaqBase, find_answer, normalize_text, parse_faq

SAMPLE = """# izoh, e'tiborga olinmaydi
## Birinchi mavzu
Kalit so'zlar: parol, unutdim, parolni unut
Birinchi javob.
Ikkinchi qator.

## Ikkinchi mavzu
Kalit so‘zlar: yangi parol, almashtir, parol
Ikkinchi javob.

## Javobsiz mavzu
Kalit so'zlar: bo'sh
"""


def test_parse_faq():
    entries = parse_faq(SAMPLE)
    assert [e.title for e in entries] == ["Birinchi mavzu", "Ikkinchi mavzu"]  # javobsiz mavzu tashlanadi
    assert entries[0].answer == "Birinchi javob.\nIkkinchi qator."
    assert entries[1].keywords == ("yangi parol", "almashtir", "parol")


def test_normalize_text():
    assert normalize_text("Паролимни УНУТДИМ!") == "parolimni unutdim"
    assert normalize_text("O‘qish, g`oya?") == "o'qish g'oya"
    assert normalize_text("ўқиш ғоя") == "o'qish g'oya"


def test_find_answer_scoring():
    entries = parse_faq(SAMPLE)
    assert find_answer(entries, "Parolimni unutdim").title == "Birinchi mavzu"
    assert find_answer(entries, "yangi parol qanday qo'yaman").title == "Ikkinchi mavzu"
    assert find_answer(entries, "parol").title == "Birinchi mavzu"  # teng -> yuqoridagisi
    assert find_answer(entries, "Паролимни унутдим").title == "Birinchi mavzu"


def test_no_answer_is_not_invented():
    entries = parse_faq(SAMPLE)
    for q in ("salom", "", "   ", "😀", "1234567"):
        assert find_answer(entries, q) is None


def test_reload_and_missing_file(tmp_path):
    path = tmp_path / "faq.txt"
    base = FaqBase(path)
    assert base.entries() == [] and base.find("parol") is None
    path.write_text(SAMPLE, encoding="utf-8")
    assert base.find("almashtir").title == "Ikkinchi mavzu"
    path.write_text("## Yangi\nKalit so'zlar: almashtir\nYangi javob\n", encoding="utf-8")
    os.utime(path, (time.time() + 5, time.time() + 5))
    assert base.find("almashtir").answer == "Yangi javob"


def test_project_faq_file_is_valid():
    from config import BASE_DIR
    entries = FaqBase(BASE_DIR / "faq.txt").entries()
    assert len(entries) >= 5
    assert all(e.keywords and e.answer for e in entries)
