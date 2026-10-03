"""Loyiha sozlamalari. Maxfiy qiymatlar faqat .env / environment orqali olinadi."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


# Bot token faqat .env yoki environment o'zgaruvchisidan olinadi
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# Webhook sozlamalari (WEBHOOK_HOST bo'lsa webhook, bo'lmasa polling ishlaydi)
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "").strip().rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip() or None
PORT = int(os.environ.get("PORT", 10000))

# Talabalar ro'yxati (Excel) va ma'lumotlar bazasi
EXCEL_FILE = _path(os.environ.get("EXCEL_FILE", "data.xlsx"))
DATABASE_FILE = _path(os.environ.get("DATABASE_FILE", "bot_data.db"))

STUDENT_SITE_URL = "https://student.kiu.uz"
STUDENT_SITE_NAME = "student.kiu.uz"
