"""Ro'yxatdan o'tish bosqichlari: F.I.Sh. -> telefon -> pasport -> tasdiqlash."""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from handlers import keyboards as kb
from handlers import texts
from handlers.states import Registration
from services.validation_service import (
    display_name,
    normalize_phone,
    validate_name,
    validate_passport,
    validate_phone,
)

logger = logging.getLogger(__name__)
router = Router(name="registration")


async def begin_registration(message: Message, state: FSMContext) -> None:
    """Eski vaqtinchalik ma'lumotlarni tozalab, 1-bosqichdan boshlaydi."""
    await state.clear()
    await state.set_state(Registration.waiting_name)
    await message.answer(texts.ASK_NAME, reply_markup=kb.REMOVE)


async def send_step_prompt(message: Message, state: FSMContext) -> None:
    """Foydalanuvchi turgan bosqich savolini qayta yuboradi."""
    current = await state.get_state()
    if current == Registration.waiting_name.state:
        await message.answer(texts.ASK_NAME, reply_markup=kb.REMOVE)
    elif current == Registration.waiting_phone.state:
        await message.answer(texts.ASK_PHONE, reply_markup=kb.phone_kb())
    elif current == Registration.waiting_passport.state:
        await message.answer(texts.ASK_PASSPORT, reply_markup=kb.REMOVE)
    elif current == Registration.confirming_data.state:
        await send_confirmation(message, state)


async def send_confirmation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(
        texts.confirm_data(display_name(data["full_name"]), data["phone"], data["passport"]),
        reply_markup=kb.confirm_kb(),
    )


# ---------------- 1. F.I.Sh. ----------------

@router.message(Registration.waiting_name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    full_name = validate_name(message.text)
    if not full_name:
        await message.answer(texts.INVALID_NAME)
        return
    await state.update_data(full_name=full_name)
    await state.set_state(Registration.waiting_phone)
    await message.answer(texts.ASK_PHONE, reply_markup=kb.phone_kb())


# ---------------- 2. Telefon ----------------

@router.message(Registration.waiting_phone, F.contact)
async def process_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    # Faqat foydalanuvchining o'z Telegram akkauntiga tegishli raqam qabul qilinadi
    if not message.from_user or contact.user_id != message.from_user.id:
        await message.answer(texts.FOREIGN_CONTACT, reply_markup=kb.phone_kb())
        return
    phone = normalize_phone(contact.phone_number)
    if not phone:
        await message.answer(texts.UNSUPPORTED_CONTACT, reply_markup=kb.phone_kb())
        return
    await _accept_phone(message, state, phone)


@router.message(Registration.waiting_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext) -> None:
    phone = validate_phone(message.text)
    if not phone:
        await message.answer(texts.INVALID_PHONE, reply_markup=kb.phone_kb())
        return
    await _accept_phone(message, state, phone)


async def _accept_phone(message: Message, state: FSMContext, phone: str) -> None:
    await state.update_data(phone=phone)
    await state.set_state(Registration.waiting_passport)
    await message.answer(texts.ASK_PASSPORT, reply_markup=kb.REMOVE)


# ---------------- 3. Pasport ----------------

@router.message(Registration.waiting_passport, F.text)
async def process_passport(message: Message, state: FSMContext) -> None:
    passport = validate_passport(message.text)
    if not passport:
        await message.answer(texts.INVALID_PASSPORT)
        return
    await state.update_data(passport=passport)
    await state.set_state(Registration.confirming_data)
    await send_confirmation(message, state)


# ---------------- 4. Tasdiqlash: qayta kiritish / bekor qilish ----------------

@router.callback_query(F.data == kb.CB_EDIT, Registration.confirming_data)
async def edit_data(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await begin_registration(callback.message, state)


@router.callback_query(F.data == kb.CB_CANCEL, Registration.confirming_data)
async def cancel_registration(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(texts.CANCELLED, reply_markup=kb.REMOVE)
    await callback.message.answer(texts.WELCOME, reply_markup=kb.register_kb())


@router.message(Registration.confirming_data)
async def confirmation_expected(message: Message, state: FSMContext) -> None:
    await message.answer(texts.CHOOSE_BUTTON)
    await send_confirmation(message, state)
