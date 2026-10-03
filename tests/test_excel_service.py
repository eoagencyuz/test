import os
import time

import pytest

from bot import (
    ExcelDataError,
    StudentRegistry,
    find_hemis_id_column,
    find_name_columns,
    find_passport_column,
    find_phone_column,
    load_students,
)
from tests.conftest import write_workbook


@pytest.mark.parametrize("header", ["HEMIS ID", "HEMIS_ID", "HEMISID", "Hemis ID", "hemis id raqami"])
def test_find_hemis_id_column(header):
    assert find_hemis_id_column(["F.I.Sh.", header]) == 1


@pytest.mark.parametrize("header", ["Telefon", "Telefon raqam", "Phone", "Telefon №"])
def test_find_phone_column(header):
    assert find_phone_column(["F.I.Sh.", header]) == 1


@pytest.mark.parametrize("header", ["Pasport", "Passport", "Pasport seriya", "Pasport seriya va raqami"])
def test_find_passport_column(header):
    assert find_passport_column(["F.I.Sh.", header]) == 1


def test_find_name_columns():
    assert find_name_columns(["F.I.O", "x"])["full_name"] == 0
    assert find_name_columns(["№", "F.I.Sh."])["full_name"] == 1
    cols = find_name_columns(["Familiya", "Ism", "Otasining ismi"])
    assert (cols["surname"], cols["first_name"], cols["patronymic"]) == (0, 1, 2)


def test_direction_column(excel_file):
    from bot import find_direction_column
    for header in ("Yo'nalish", "Ta’lim yo‘nalishi", "Mutaxassislik", "Specialty"):
        assert find_direction_column(["F.I.Sh.", header]) == 1
    s = StudentRegistry(excel_file).find_student("TESTOV ALPHA", "998901112233", "TT1111111")
    assert s.direction == "Test yo‘nalishi"


def test_hemis_id_is_taken_as_is(excel_file):
    students = load_students(excel_file)
    ids = {s.hemis_id for s in students}
    # Raqam ko'rinishidagi katak ham o'zgarishsiz matnga aylanadi; bo'sh ID o'tkazib yuboriladi
    assert ids == {"300000000001", "300000000002", "300000000003", "300000000004"}


# ---- TEST 11: Excelda mavjud talaba ----

def test_found_with_all_fields(excel_file):
    reg = StudentRegistry(excel_file)
    s = reg.find_student("TESTOV ALPHA", "998901112233", "TT1111111")
    assert s and s.hemis_id == "300000000001"
    # Otasining ismi bilan va apostrof variantlari bilan
    s = reg.find_student("TESTOV ALPHA BETA O'G'LI", "998901112233", "TT1111111")
    assert s and s.hemis_id == "300000000001"
    # Excel'da telefon +998 va bo'sh joylar bilan yozilgan
    s = reg.find_student("SINOVOVA GAMMA", "998934445566", "TS2222222")
    assert s and s.hemis_id == "300000000002"


# ---- TEST 12: mavjud bo'lmagan talaba ----

@pytest.mark.parametrize("name, phone, passport", [
    ("NOMALUM TALABA", "998900000000", "XX0000000"),          # umuman yo'q
    ("TESTOV ALPHA", "998901112233", "TT9999999"),            # pasport mos emas
    ("TESTOV ALPHA", "998909999999", "TT1111111"),            # telefon mos emas
    ("BOSHQA ISM", "998901112233", "TT1111111"),              # ism mos emas
    ("BOSHID ZETA", "998907770000", "TZ5555555"),             # Excel'da HEMIS ID bo'sh
])
def test_not_found(excel_file, name, phone, passport):
    assert StudentRegistry(excel_file).find_student(name, phone, passport) is None


def test_name_only_never_returns_hemis_id(excel_file):
    assert StudentRegistry(excel_file).find_student("TESTOV ALPHA", None, None) is None


# ---- TEST 13: bir xil ism-familiya ----

def test_same_name_resolved_by_phone_and_passport(excel_file):
    reg = StudentRegistry(excel_file)
    assert reg.find_student("BIRXIL EPSILON", "998905550001", "TQ3333333").hemis_id == "300000000003"
    assert reg.find_student("BIRXIL EPSILON", "998905550002", "TQ4444444").hemis_id == "300000000004"
    # Bitta talabaning pasporti, boshqasining telefoni -> rad etiladi
    assert reg.find_student("BIRXIL EPSILON", "998905550002", "TQ3333333") is None


def test_ambiguous_match_returns_nothing(tmp_path):
    rows = [
        [1, "IKKI NUSXA", "901000000", "TA1000000", 1001],
        [2, "IKKI NUSXA", "901000000", "TA1000000", 1002],
    ]
    path = write_workbook(tmp_path / "dup.xlsx", rows=rows)
    assert StudentRegistry(path).find_student("IKKI NUSXA", "998901000000", "TA1000000") is None


def test_separate_name_columns_and_title_rows(tmp_path):
    headers = ["Familiya", "Ism", "Otasining ismi", "Phone", "Passport", "HEMIS_ID"]
    rows = [["Omega", "Theta", "Kappa", "998911234500", "tk 7777777", "ID-77"]]
    path = write_workbook(tmp_path / "sep.xlsx", headers=headers, rows=rows, title_rows=2)
    s = StudentRegistry(path).find_student("OMEGA THETA", "911234500", "TK7777777")
    assert s and s.hemis_id == "ID-77"


def test_missing_file_and_missing_hemis_column(tmp_path):
    with pytest.raises(ExcelDataError):
        StudentRegistry(tmp_path / "none.xlsx").students()
    path = write_workbook(tmp_path / "nohemis.xlsx", headers=["F.I.Sh.", "Pasport"], rows=[["A B", "AA1"]])
    with pytest.raises(ExcelDataError):
        StudentRegistry(path).students()


def test_registry_reloads_when_file_changes(tmp_path):
    path = write_workbook(tmp_path / "s.xlsx", rows=[[1, "YANGI TALABA", "901231231", "TY1231231", 555]])
    reg = StudentRegistry(path)
    assert reg.find_student("YANGI TALABA", "901231231", "TY1231231").hemis_id == "555"
    write_workbook(path, rows=[[1, "YANGI TALABA", "901231231", "TY1231231", 556]])
    os.utime(path, (time.time() + 5, time.time() + 5))
    assert reg.find_student("YANGI TALABA", "901231231", "TY1231231").hemis_id == "556"


def test_name_matching_tolerates_hyphens_apostrophes_and_karakalpak_letters():
    from bot import _name_matches
    assert _name_matches("FAMILIYA ABDURAHMON", "FAMILIYA ABDU-RAHMON ALIYEVICH")
    assert _name_matches("FAMILIYA ABDU RAHMON", "FAMILIYA ABDU-RAHMON")
    assert _name_matches("FAMILIYA ISM OTA O'G'LI", "FAMILIYA ISM OTA-O‘G‘LI")
    assert _name_matches("GULOMOV ISM", "G'ULOMOV ISM")
    assert _name_matches("FAMILIYA ISM OTA OGLI", "FAMILIYA ISM OTA ÓǴLI")
    assert _name_matches("FAMILIYA ISM OTA", "FAMILIYA ISM OTA'")
    # Faqat to'liq so'zlar: qisqa ism uzunroq ismga mos kelmaydi
    assert not _name_matches("FAMILIYA ALI", "FAMILIYA ALISHER")
    assert not _name_matches("FAMILIYA", "FAMILIYAXON ISM")
    assert not _name_matches("BOSHQA ISM", "FAMILIYA ISM")
    assert not _name_matches("", "FAMILIYA ISM")
