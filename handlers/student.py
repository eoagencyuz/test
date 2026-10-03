"""Tasdiqlangan ma'lumotlar bo'yicha Excel'dan talabani topish va HEMIS ID berish."""
import asyncio
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from database.database import Database
from handlers import keyboards as kb
from handlers import texts
from handlers.states import Registration
from services.excel_service import ExcelDataError, StudentRegistry
from services.validation_service import display_name, mask_value

logger = logging.getLogger(__name__)
router = Router(name="student")


@router.callback_query(F.data == kb.CB_CONFIRM, Registration.confirming_data)
async def confirm_and_search(callback: CallbackQuery, state: FSMContext,
                             db: Database, registry: StudentRegistry) -> None:
    user = callback.from_user
    message = callback.message
    data = await state.get_data()

    # Ikki marta bosilishining oldini olish
    await state.set_state(Registration.searching_student)
    await callback.answer()
    await message.edit_reply_markup(reply_markup=None)
    await message.answer(texts.SEARCHING)

    try:
        student = await asyncio.to_thread(
            registry.find_student, data["full_name"], data["phone"], data["passport"]
        )
    except ExcelDataError as e:
        logger.error("Excel bilan ishlashda xatolik (user_id=%s): %s", user.id, e)
        await state.set_state(Registration.confirming_data)
        await message.answer(texts.SERVICE_UNAVAILABLE, reply_markup=kb.confirm_kb())
        return
    except Exception:
        logger.exception("Talabani qidirishda kutilmagan xatolik (user_id=%s)", user.id)
        await state.set_state(Registration.confirming_data)
        await message.answer(texts.SERVICE_UNAVAILABLE, reply_markup=kb.confirm_kb())
        return

    if student is None:
        logger.info("Talaba topilmadi (user_id=%s)", user.id)
        await state.clear()
        await message.answer(texts.NOT_FOUND, reply_markup=kb.reregister_kb())
        return

    # HEMIS ID Excel'dagi qiymatning o'zi
    hemis_id = student.hemis_id
    full_name = display_name(data["full_name"])
    await asyncio.to_thread(
        db.save_user, user.id, user.username, data["full_name"],
        data["phone"], data["passport"], hemis_id,
    )
    await state.clear()
    logger.info("Ro'yxatdan o'tdi (user_id=%s, hemis_id=%s)", user.id, mask_value(hemis_id))

    await message.answer(texts.verified(full_name, data["phone"], data["passport"], hemis_id))
    await message.answer(texts.login_instructions(hemis_id, data["passport"]), reply_markup=kb.site_kb())
    await message.answer(texts.completed(hemis_id), reply_markup=kb.site_and_reregister_kb())
