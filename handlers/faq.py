"""Savol-javob: talaba yozgan savolga faq.txt dagi tayyor javobni qaytaradi."""
import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message

from handlers import keyboards as kb
from handlers import texts
from services.faq_service import FaqBase

logger = logging.getLogger(__name__)
router = Router(name="faq")


async def send_faq_list(message: Message, faq: FaqBase) -> None:
    entries = await asyncio.to_thread(faq.entries)
    if not entries:
        await message.answer(texts.FAQ_EMPTY)
        return
    await message.answer(texts.FAQ_LIST, reply_markup=kb.faq_list_kb([e.title for e in entries]))


@router.message(Command("faq", "help"), StateFilter(None))
async def faq_command(message: Message, faq: FaqBase) -> None:
    await send_faq_list(message, faq)


@router.callback_query(F.data == kb.CB_FAQ_LIST)
async def faq_list_button(callback: CallbackQuery, faq: FaqBase) -> None:
    await callback.answer()
    await send_faq_list(callback.message, faq)


@router.callback_query(F.data.startswith(kb.CB_FAQ_ITEM))
async def faq_item_button(callback: CallbackQuery, faq: FaqBase) -> None:
    entries = await asyncio.to_thread(faq.entries)
    index = callback.data[len(kb.CB_FAQ_ITEM):]
    if not index.isdigit() or int(index) >= len(entries):
        # Fayl o'zgargan bo'lsa, eski tugma boshqa mavzuga tushib qolmasligi uchun
        await callback.answer(texts.STALE_BUTTON, show_alert=True)
        return
    await callback.answer()
    entry = entries[int(index)]
    await callback.message.answer(f"❓ {entry.title}\n\n{entry.answer}", reply_markup=kb.faq_more_kb())


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def answer_question(message: Message, faq: FaqBase) -> None:
    entry = await asyncio.to_thread(faq.find, message.text)
    if entry is None:
        # Savol matni loglarga yozilmaydi (shaxsiy ma'lumot bo'lishi mumkin)
        logger.info("Savolga javob topilmadi (user_id=%s)", message.from_user.id if message.from_user else None)
        entries = await asyncio.to_thread(faq.entries)
        markup = kb.faq_list_kb([e.title for e in entries]) if entries else None
        await message.answer(texts.FAQ_NOT_FOUND, reply_markup=markup)
        return
    await message.answer(entry.answer, reply_markup=kb.faq_more_kb())
