"""/start, ro'yxatdan o'tishni boshlash, qayta ro'yxatdan o'tish va boshqa xabarlar."""
import asyncio

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.database import Database
from handlers import keyboards as kb
from handlers import texts
from handlers.registration import begin_registration, send_step_prompt
from handlers.states import IN_PROGRESS_STATES, Registration

router = Router(name="start")
# Boshqa routerlar ishlamagan xabarlar uchun (eng oxirida ulanadi)
fallback_router = Router(name="fallback")


async def show_home(message: Message, user_id: int, db: Database) -> None:
    """Ro'yxatdan o'tgan bo'lsa HEMIS IDni, aks holda boshlang'ich menyuni ko'rsatadi."""
    registered = await asyncio.to_thread(db.get_user, user_id)
    if registered:
        await message.answer(
            texts.already_registered(registered.hemis_id),
            reply_markup=kb.site_and_reregister_kb(),
        )
    else:
        await message.answer(texts.WELCOME, reply_markup=kb.register_kb())


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, db: Database) -> None:
    current = await state.get_state()
    if current == Registration.searching_student.state:
        await message.answer(texts.STILL_SEARCHING)
        return
    if current in {s.state for s in IN_PROGRESS_STATES}:
        await message.answer(texts.REGISTRATION_IN_PROGRESS)
        await send_step_prompt(message, state)
        return
    await state.clear()
    await show_home(message, message.from_user.id, db)


@router.message(Command("cancel"), StateFilter(*IN_PROGRESS_STATES))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=kb.REMOVE)
    await message.answer(texts.WELCOME, reply_markup=kb.register_kb())


@router.callback_query(F.data.in_({kb.CB_REGISTER, kb.CB_REREGISTER}))
async def register_button(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state() == Registration.searching_student.state:
        await callback.answer(texts.STILL_SEARCHING, show_alert=True)
        return
    await callback.answer()
    await begin_registration(callback.message, state)


# ---------------- Fallback ----------------

@fallback_router.message(Registration.searching_student)
async def while_searching(message: Message) -> None:
    await message.answer(texts.STILL_SEARCHING)


@fallback_router.message(StateFilter(*IN_PROGRESS_STATES))
async def non_text_input(message: Message) -> None:
    """Rasm, video, stiker, ovozli xabar, fayl va h.k. yuborilganda."""
    await message.answer(texts.TEXT_REQUIRED)


@fallback_router.message()
async def idle_message(message: Message, db: Database) -> None:
    if not message.from_user:
        return
    await show_home(message, message.from_user.id, db)


@fallback_router.callback_query()
async def stale_callback(callback: CallbackQuery) -> None:
    await callback.answer(texts.STALE_BUTTON, show_alert=True)
