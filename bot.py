import logging
import os
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import asyncio

TOKEN = os.environ.get("BOT_TOKEN", "6752000695:AAF7w4udv0wW0qhhogOno9H5YKTBaZ35p6U")

# Webhook sozlamalari (WEBHOOK_HOST bo'lsa webhook, bo'lmasa polling ishlaydi)
WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "").rstrip("/")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

EXCEL_FILE = 'data.xlsx'

def get_student_info(jshshir_input):
    try:
        df = pd.read_excel(EXCEL_FILE, dtype=str)

        # JSHSHIR 2-ustunda (B ustuni, indeks 1)
        jshshir_col_idx = 1

        result = df[df.iloc[:, jshshir_col_idx].str.strip() == str(jshshir_input).strip()]

        if not result.empty:
            row = result.iloc[0]
            fio = row.iloc[2]        # F.I.O (C ustuni)
            yonalish = row.iloc[5]   # Yo'nalish (F ustuni)
            ball = row.iloc[6]       # Ball (G ustuni)

            return (
                f"Hurmatli {fio}!\n"
                f"Sizning o'qishni ko'chirish bo'yicha topshirgan test imtihoningiz natijasi aniqlandi.\n\n"
                f"JSHSHIR: {jshshir_input}\n"
                f"F.I.Sh.: {fio}\n"
                f"Yo'nalish: {yonalish}\n"
                f"Test natijasi: {ball} ball"
            )
        else:
            return "Kiritilgan JSHSHIR bo'yicha ma'lumot topilmadi. Qaytadan tekshirib ko'ring."

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        return "Ma'lumotlarni o'qishda xatolik yuz berdi."


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Assalomu alaykum! Imtihon natijasini bilish uchun JSHSHIR raqamingizni yuboring."
    )


@dp.message()
async def check_result(message: types.Message):
    user_text = message.text.strip()

    if user_text.isdigit() and len(user_text) == 14:
        await message.answer("Ma'lumot qidirilmoqda...")
        response_text = get_student_info(user_text)
        await message.answer(response_text)
    else:
        await message.answer("Iltimos, faqat 14 xonali JSHSHIR raqamini kiriting.")


async def on_startup(bot: Bot):
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")
    else:
        await bot.delete_webhook(drop_pending_updates=True)


async def on_shutdown(bot: Bot):
    if WEBHOOK_URL:
        await bot.delete_webhook()


def main():
    logging.basicConfig(level=logging.INFO)

    if WEBHOOK_URL:
        # Web Service rejimi: Render port kutadi, shu sabab webhook ishlatamiz
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        async def health(request):
            return web.Response(text="OK")

        app.router.add_get("/", health)

        web.run_app(app, host="0.0.0.0", port=PORT)
    else:
        # Lokal ishga tushirish uchun polling
        async def run_polling():
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)

        asyncio.run(run_polling())


if __name__ == '__main__':
    main()
