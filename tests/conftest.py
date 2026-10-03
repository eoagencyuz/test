import os
import sys
import tempfile
from pathlib import Path

import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Testlar haqiqiy baza/Excel fayliga tegmasligi uchun
_TMP = Path(tempfile.mkdtemp(prefix="bot-tests-"))
os.environ["DATABASE_FILE"] = str(_TMP / "test.db")
os.environ["EXCEL_FILE"] = str(_TMP / "missing.xlsx")
os.environ["BOT_TOKEN"] = ""

# Soxta (synthetic) talabalar: faqat test uchun, real ma'lumot emas
HEADERS = ["№", "F.I.Sh.", "Telefon raqam", "Pasport seriya va raqami", "HEMIS ID", "Ta'lim yo'nalishi"]
ROWS = [
    [1, "TESTOV ALPHA BETA O‘G‘LI", "901112233", "TT 1111111", 300000000001, "Test  yo‘nalishi"],
    [2, "SINOVOVA GAMMA DELTA QIZI", "+998 93 444 55 66", "TS2222222", "300000000002"],
    # Bir xil ism-familiyali ikki talaba
    [3, "BIRXIL EPSILON", "905550001", "TQ3333333", 300000000003],
    [4, "BIRXIL EPSILON", "905550002", "TQ4444444", 300000000004],
    # HEMIS ID bo'sh -- hech qachon qaytarilmasligi kerak
    [5, "BOSHID ZETA", "907770000", "TZ5555555", None],
]


def write_workbook(path: Path, headers=HEADERS, rows=ROWS, title_rows=0) -> Path:
    wb = Workbook()
    ws = wb.active
    for _ in range(title_rows):
        ws.append(["Talabalar ro'yxati"])
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


@pytest.fixture
def excel_file(tmp_path) -> Path:
    return write_workbook(tmp_path / "students.xlsx")
