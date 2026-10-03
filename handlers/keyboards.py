from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import STUDENT_SITE_URL

CB_REGISTER = "reg:start"
CB_REREGISTER = "reg:restart"
CB_CONFIRM = "reg:confirm"
CB_EDIT = "reg:edit"
CB_CANCEL = "reg:cancel"

PHONE_BUTTON_TEXT = "📱 Telefon raqamni yuborish"

REMOVE = ReplyKeyboardRemove()


def register_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Ro‘yxatdan o‘tish", callback_data=CB_REGISTER)],
    ])


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=PHONE_BUTTON_TEXT, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=CB_CONFIRM)],
        [InlineKeyboardButton(text="✏️ Qayta kiritish", callback_data=CB_EDIT)],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=CB_CANCEL)],
    ])


def site_and_reregister_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Student tizimiga kirish", url=STUDENT_SITE_URL)],
        [InlineKeyboardButton(text="🔄 Qayta ro‘yxatdan o‘tish", callback_data=CB_REREGISTER)],
    ])


def reregister_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Qayta ro‘yxatdan o‘tish", callback_data=CB_REREGISTER)],
    ])
