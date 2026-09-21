import logging
import os
import json
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

# O'tish balli chegarasi: shundan yuqori (yoki teng) bo'lsa talab bajarilgan hisoblanadi
PASS_THRESHOLD = 56.7


def parse_ball(ball_raw: str):
    """Ball qiymatini (vergul yoki nuqta bilan yozilgan bo'lishi mumkin) songa aylantiradi."""
    try:
        return float(str(ball_raw).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def lookup_student(jshshir_input: str):
    """
    JSHSHIR bo'yicha talaba ma'lumotini qidiradi.
    Natija: dict {"found": bool, "fio":.., "talim_shakli":.., "yonalish":.., "ball":.., "holat":.., "jshshir":..}
    yoki {"found": False, "error": "..."}
    """
    try:
        df = pd.read_excel(EXCEL_FILE, dtype=str)

        # JSHSHIR 2-ustunda (B ustuni, indeks 1)
        jshshir_col_idx = 1

        result = df[df.iloc[:, jshshir_col_idx].str.strip() == str(jshshir_input).strip()]

        if not result.empty:
            row = result.iloc[0]
            fio = row.iloc[2]           # F.I.O (C ustuni)
            talim_shakli = row.iloc[4]  # Ta'lim shakli (E ustuni)
            yonalish = row.iloc[5]      # Yo'nalish (F ustuni)
            ball = row.iloc[6]          # Ball (G ustuni)

            ball_num = parse_ball(ball)
            if ball_num is None:
                holat = "Aniqlanmadi"
            elif ball_num >= PASS_THRESHOLD:
                holat = "Talab bajarildi"
            else:
                holat = "Talab bajarilmadi"

            return {
                "found": True,
                "jshshir": jshshir_input,
                "fio": str(fio),
                "talim_shakli": str(talim_shakli),
                "yonalish": str(yonalish),
                "ball": str(ball),
                "holat": holat,
            }
        else:
            return {"found": False, "error": "Kiritilgan JSHSHIR bo'yicha ma'lumot topilmadi. Qaytadan tekshirib ko'ring."}

    except Exception as e:
        logging.error(f"Xatolik: {e}")
        return {"found": False, "error": "Ma'lumotlarni o'qishda xatolik yuz berdi."}


def format_result_text(info: dict) -> str:
    if not info.get("found"):
        return info.get("error", "Xatolik yuz berdi.")
    return (
        f"Hurmatli {info['fio']}!\n"
        f"Sizning o'qishni ko'chirish bo'yicha topshirgan test imtihoningiz natijasi aniqlandi.\n\n"
        f"JSHSHIR: {info['jshshir']}\n"
        f"F.I.Sh.: {info['fio']}\n"
        f"Ta'lim shakli: {info['talim_shakli']}\n"
        f"Yo'nalish: {info['yonalish']}\n"
        f"Test natijasi: {info['ball']} ball\n"
        f"Holat: {info['holat']}"
    )


# ---------------- Telegram bot handlerlari ----------------

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
        info = lookup_student(user_text)
        await message.answer(format_result_text(info))
    else:
        await message.answer("Iltimos, faqat 14 xonali JSHSHIR raqamini kiriting.")


# ---------------- Veb-sahifa (natija tekshirish sayti) ----------------

HTML_PAGE = """<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Imtihon natijasini tekshirish</title>
<style>
  :root {
    --bg: #0f172a;
    --card: #ffffff;
    --accent: #2563eb;
    --accent-dark: #1d4ed8;
    --text: #1e293b;
    --muted: #64748b;
    --error: #dc2626;
    --success: #16a34a;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    padding: 20px;
  }
  .card {
    background: var(--card);
    border-radius: 16px;
    padding: 32px 28px;
    max-width: 420px;
    width: 100%;
    box-shadow: 0 20px 50px rgba(0,0,0,0.35);
  }
  h1 {
    font-size: 20px;
    color: var(--text);
    margin: 0 0 6px;
    text-align: center;
  }
  p.subtitle {
    color: var(--muted);
    font-size: 14px;
    text-align: center;
    margin: 0 0 24px;
  }
  label {
    font-size: 13px;
    color: var(--muted);
    display: block;
    margin-bottom: 6px;
  }
  input[type="text"] {
    width: 100%;
    padding: 14px 16px;
    font-size: 18px;
    letter-spacing: 1px;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    outline: none;
    transition: border-color 0.15s;
  }
  input[type="text"]:focus {
    border-color: var(--accent);
  }
  button {
    width: 100%;
    margin-top: 16px;
    padding: 14px;
    font-size: 16px;
    font-weight: 600;
    color: #fff;
    background: var(--accent);
    border: none;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.15s;
  }
  button:hover { background: var(--accent-dark); }
  button:disabled { background: #94a3b8; cursor: not-allowed; }

  #result {
    margin-top: 22px;
    padding: 18px;
    border-radius: 10px;
    display: none;
    font-size: 14px;
    line-height: 1.6;
  }
  #result.success {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #14532d;
    display: block;
  }
  #result.error {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: var(--error);
    display: block;
  }
  .row { display:flex; justify-content:space-between; gap:10px; padding: 4px 0; border-bottom: 1px dashed #d1fae5; }
  .row:last-child { border-bottom: none; }
  .row .k { color:#166534; font-weight:500; }
  .row .v { color:#14532d; font-weight:600; text-align:right; }
  .status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 13px;
  }
  .status-ok { background:#16a34a; color:#fff; }
  .status-fail { background:#dc2626; color:#fff; }
  .footer {
    text-align: center;
    margin-top: 20px;
    font-size: 12px;
    color: var(--muted);
  }
  .uni-logo {
    display: block;
    max-width: 280px;
    width: 70%;
    height: auto;
    margin-bottom: 20px;
    filter: drop-shadow(0 2px 8px rgba(0,0,0,0.25));
    background: #fff;
    border-radius: 10px;
    padding: 10px 16px;
  }
</style>
</head>
<body>
  <img class="uni-logo" src="data:image/png;base64,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" alt="Qarshi xalqaro universiteti">
  <div class="card">
    <h1>Imtihon natijasini tekshirish</h1>
    <p class="subtitle">O'qishni ko'chirish bo'yicha test natijangizni bilish uchun JSHSHIR raqamingizni kiriting</p>

    <label for="jshshir">JSHSHIR (14 xonali)</label>
    <input type="text" id="jshshir" inputmode="numeric" maxlength="14" placeholder="00000000000000" autocomplete="off">
    <button id="checkBtn" onclick="checkResult()">Tekshirish</button>

    <div id="result"></div>

    <div class="footer">Qarshi Xalqaro Universiteti</div>
  </div>

<script>
async function checkResult() {
  const input = document.getElementById('jshshir');
  const btn = document.getElementById('checkBtn');
  const resultBox = document.getElementById('result');
  const value = input.value.trim();

  resultBox.className = '';
  resultBox.style.display = 'none';

  if (!/^\\d{14}$/.test(value)) {
    resultBox.className = 'error';
    resultBox.textContent = "Iltimos, faqat 14 xonali JSHSHIR raqamini kiriting.";
    return;
  }

  btn.disabled = true;
  btn.textContent = "Qidirilmoqda...";

  try {
    const res = await fetch('/api/check?jshshir=' + encodeURIComponent(value));
    const data = await res.json();

    if (data.found) {
      resultBox.className = 'success';
      const statusClass = data.holat === 'Talab bajarildi' ? 'status-ok' : 'status-fail';
      resultBox.innerHTML =
        '<div class="row"><span class="k">F.I.Sh.</span><span class="v">' + data.fio + '</span></div>' +
        '<div class="row"><span class="k">Ta\\'lim shakli</span><span class="v">' + data.talim_shakli + '</span></div>' +
        '<div class="row"><span class="k">Yo\\'nalish</span><span class="v">' + data.yonalish + '</span></div>' +
        '<div class="row"><span class="k">Test natijasi</span><span class="v">' + data.ball + ' ball</span></div>' +
        '<div class="row"><span class="k">Holat</span><span class="v"><span class="status-badge ' + statusClass + '">' + data.holat + '</span></span></div>';
    } else {
      resultBox.className = 'error';
      resultBox.textContent = data.error || "Ma'lumot topilmadi.";
    }
  } catch (e) {
    resultBox.className = 'error';
    resultBox.textContent = "Server bilan bog'lanishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.";
  } finally {
    btn.disabled = false;
    btn.textContent = "Tekshirish";
  }
}

document.getElementById('jshshir').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') checkResult();
});
document.getElementById('jshshir').addEventListener('input', function(e) {
  e.target.value = e.target.value.replace(/\\D/g, '').slice(0, 14);
});
</script>
</body>
</html>
"""


async def index_page(request):
    return web.Response(text=HTML_PAGE, content_type="text/html")


async def api_check(request):
    jshshir = request.query.get("jshshir", "").strip()
    if not (jshshir.isdigit() and len(jshshir) == 14):
        return web.json_response({"found": False, "error": "JSHSHIR 14 xonali raqamdan iborat bo'lishi kerak."})
    info = lookup_student(jshshir)
    return web.json_response(info)


async def health(request):
    return web.Response(text="OK")


# ---------------- Webhook / polling ishga tushirish ----------------

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

        # Veb-sahifa va API
        app.router.add_get("/", index_page)
        app.router.add_get("/api/check", api_check)
        app.router.add_get("/health", health)

        web.run_app(app, host="0.0.0.0", port=PORT)
    else:
        # Lokal ishga tushirish uchun polling
        async def run_polling():
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)

        asyncio.run(run_polling())


if __name__ == '__main__':
    main()
