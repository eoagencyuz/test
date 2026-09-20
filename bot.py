import logging
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

TOKEN = "6752000695:AAF7w4udv0wW0qhhogOno9H5YKTBaZ35p6U"

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
            fio = row.iloc[2]      # F.I.O (C ustuni)
            yonalish = row.iloc[5] # Yo'nalish (F ustuni)
            ball = row.iloc[6]     # Ball (G ustuni)
            
            return (
                f"Hurmatli {fio}!\n"
                f"Sizning o‘qishni ko‘chirish bo‘yicha topshirgan test imtihoningiz natijasi aniqlandi.\n\n"
                f"🪪 JSHSHIR: {jshshir_input}\n"
                f"👤 F.I.Sh.: {fio}\n"
                f"📚 Yo‘nalish: {yonalish}\n"
                f"📝 Test natijasi: {ball} ball"
            )
        else:
            return "❌ Kiritilgan JSHSHIR bo'yicha ma'lumot topilmadi. Qaytadan tekshirib ko'ring."
            
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        return "⚠️ Ma'lumotlarni o'qishda xatolik yuz berdi."

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    # Siz xohlagan aniq matn
    await message.answer(
        "Assalomu alaykum! Imtihon natijasini bilish uchun JSHSHIR raqamingizni yuboring."
    )

@dp.message()
async def check_result(message: types.Message):
    user_text = message.text.strip()
    
    if user_text.isdigit() and len(user_text) == 14:
        await message.answer("🔍 Ma'lumot qidirilmoqda...")
        response_text = get_student_info(user_text)
        await message.answer(response_text)
    else:
        await message.answer("⚠️ Iltimos, faqat 14 xonali JSHSHIR raqamini kiriting.")

async def main():
    # Eski webhookni tozalash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())