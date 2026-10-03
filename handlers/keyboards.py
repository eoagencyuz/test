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
CB_FAQ_LIST = "faq:list"
CB_FAQ_ITEM = "faq:"  # + mavzu tartib raqami

PHONE_BUTTON_TEXT = "📱 Telefon raqamni yuborish"

REMOVE = ReplyKeyboardRemove()


FAQ_BUTTON = InlineKeyboardButton(text="❓ Savol-javob", callback_data=CB_FAQ_LIST)


def register_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Ro‘yxatdan o‘tish", callback_data=CB_REGISTER)],
        [FAQ_BUTTON],
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


def site_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Student tizimiga kirish", url=STUDENT_SITE_URL)],
    ])


def site_and_reregister_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Student tizimiga kirish", url=STUDENT_SITE_URL)],
        [InlineKeyboardButton(text="🔄 Qayta ro‘yxatdan o‘tish", callback_data=CB_REREGISTER)],
        [FAQ_BUTTON],
    ])


def faq_list_kb(titles: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=title[:60], callback_data=f"{CB_FAQ_ITEM}{i}")]
        for i, title in enumerate(titles)
    ])


def faq_more_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Barcha savollar", callback_data=CB_FAQ_LIST)],
    ])


def reregister_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Qayta ro‘yxatdan o‘tish", callback_data=CB_REREGISTER)],
    ])
