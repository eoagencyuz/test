import pytest

from bot import (
    mask_value,
    normalize_full_name,
    normalize_passport,
    normalize_phone,
    validate_name,
    validate_passport,
    validate_phone,
)


# ---- TEST 2-4: ism/familiya ----

@pytest.mark.parametrize("value, expected", [
    ("ALIYEV VALI", "ALIYEV VALI"),
    ("KARIMOVA DILNOZA", "KARIMOVA DILNOZA"),
    ("ABDULLAYEV ALISHER BAXTIYOR", "ABDULLAYEV ALISHER BAXTIYOR"),
    ("ABDULLAYEV ALISHER BAXTIYOR O‘G‘LI", "ABDULLAYEV ALISHER BAXTIYOR O'G'LI"),
    ("abdullayev alisher baxtiyor oʻgʻli", "ABDULLAYEV ALISHER BAXTIYOR O'G'LI"),
    ("  aliyev    vali  ", "ALIYEV VALI"),
    ("SHOKIROV CHORI", "SHOKIROV CHORI"),
    ("G’ANIYEV MA`RUF", "G'ANIYEV MA'RUF"),
])
def test_valid_names(value, expected):
    assert validate_name(value) == expected


@pytest.mark.parametrize("value", [
    "АLIYEV VALI",      # birinchi harf kirill
    "АЛИЕВ ВАЛИ",       # to'liq kirill
    "ALIYEV123 VALI",
    "ALIYEV",
    "123456",
    "ALIYEV @ VALI",
    "ALIYEV VALI 😀",
    "ALIYEV-VALI",
    "'ALIYEV VALI",
    "A VALI",
    "",
    "ALIYEV VALI A'ZAM SOBIROVICH QIZI",  # 5 ta so'z
])
def test_invalid_names(value):
    assert validate_name(value) is None


# ---- TEST 5-8: telefon ----

@pytest.mark.parametrize("value, expected", [
    ("901234567", "998901234567"),
    ("912345678", "998912345678"),
    ("935678912", "998935678912"),
    ("998901234567", "998901234567"),
    ("998912345678", "998912345678"),
    (" 998935678912 ", "998935678912"),
])
def test_valid_phones(value, expected):
    assert validate_phone(value) == expected


@pytest.mark.parametrize("value", [
    "+998901234567", "998 90 123 45 67", "90 123 45 67", "12345",
    "1234567890", "99812345", "997901234567", "90-123-45-67", "", "٩٠١٢٣٤٥٦٧",
])
def test_invalid_phones(value):
    assert validate_phone(value) is None


def test_validate_phone_accepts_any_digits():
    # Hech qanday aniq raqam kutilmaydi: istalgan 9 xonali raqam qabul qilinadi
    for i in range(0, 10**9, 98765431):
        local = f"{i:09d}"
        assert validate_phone(local) == "998" + local


@pytest.mark.parametrize("value, expected", [
    ("+998901234567", "998901234567"),
    ("998 90 123-45-67", "998901234567"),
    ("901234567", "998901234567"),
    ("+7 999 123 45 67", None),
])
def test_normalize_phone(value, expected):
    assert normalize_phone(value) == expected


# ---- TEST 9-10: pasport ----

@pytest.mark.parametrize("value", ["AB1234567", "AC7654321", "KA4589213", "UZ6543210", " AD0000001 "])
def test_valid_passports(value):
    assert validate_passport(value) == value.strip()


@pytest.mark.parametrize("value", [
    "A12345678", "ABC1234567", "ab1234567", "Ab1234567", "AB123456",
    "AB12345678", "AB-1234567", "AB 1234567", "АB1234567", "",
])
def test_invalid_passports(value):
    assert validate_passport(value) is None


def test_normalize_passport_and_name():
    assert normalize_passport(" ab 123-4567 ") == "AB1234567"
    assert normalize_full_name("o`g’li  qiZi") == "O'G'LI QIZI"


def test_mask_value():
    assert mask_value("300000000001") == "30********01"
    assert "1111111" not in mask_value("TT1111111")
