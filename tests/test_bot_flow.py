"""Botning to'liq ro'yxatdan o'tish jarayoni (Telegram API soxtalashtirilgan)."""
import asyncio
import itertools
from datetime import datetime

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageReplyMarkup, SendMessage
from aiogram.types import Chat, Message, Update

import bot as bot_module
from bot import Database, SQLiteStorage
from bot import StudentRegistry

USER_ID = 1001
_ids = itertools.count(1)


class FakeSession(BaseSession):
    """Telegram'ga so'rov yubormaydi, faqat yuborilgan xabarlarni yozib boradi."""

    def __init__(self):
        super().__init__()
        self.sent: list = []

    async def make_request(self, bot, method, timeout=None):
        self.sent.append(method)
        if isinstance(method, (AnswerCallbackQuery, EditMessageReplyMarkup)):
            return True
        return Message(message_id=next(_ids), date=datetime.now(),
                       chat=Chat(id=USER_ID, type="private"), text=getattr(method, "text", None))

    async def stream_content(self, *args, **kwargs):  # pragma: no cover
        yield b""

    async def close(self):
        pass


class Client:
    def __init__(self, tmp_path, excel_file):
        self.db_path = tmp_path / "bot.db"
        self.session = FakeSession()
        self.bot = Bot(token="42:TEST", session=self.session)
        self.dp = bot_module.dp
        self.excel_file = excel_file
        self.restart()

    def restart(self):
        """Bot qayta ishga tushishi: yangi ulanish, yangi storage, o'sha baza fayli."""
        self.db = Database(self.db_path)
        self.dp.fsm.storage = SQLiteStorage(self.db)
        self.dp["db"] = self.db
        self.dp["registry"] = StudentRegistry(self.excel_file)

    def _base(self):
        return {"message_id": next(_ids), "date": int(datetime.now().timestamp()),
                "chat": {"id": USER_ID, "type": "private"},
                "from": {"id": USER_ID, "is_bot": False, "first_name": "Test", "username": "tester"}}

    async def _feed(self, update: dict) -> list[str]:
        start = len(self.session.sent)
        await self.dp.feed_update(self.bot, Update.model_validate({"update_id": next(_ids), **update},
                                                                  context={"bot": self.bot}))
        return [m.text for m in self.session.sent[start:] if isinstance(m, SendMessage)]

    async def text(self, text: str) -> list[str]:
        msg = self._base()
        msg["text"] = text
        if text.startswith("/"):
            msg["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
        return await self._feed({"message": msg})

    async def message(self, **content) -> list[str]:
        return await self._feed({"message": {**self._base(), **content}})

    async def press(self, data: str) -> list[str]:
        cb = {"id": str(next(_ids)), "from": self._base()["from"], "chat_instance": "ci", "data": data,
              "message": {**self._base(), "text": "x"}}
        return await self._feed({"callback_query": cb})

    async def state(self):
        from aiogram.fsm.storage.base import StorageKey
        return await self.dp.fsm.storage.get_state(StorageKey(bot_id=42, chat_id=USER_ID, user_id=USER_ID))

    def last_markup(self):
        sends = [m for m in self.session.sent if isinstance(m, SendMessage)]
        return sends[-1].reply_markup


@pytest.fixture
async def client(tmp_path, excel_file):
    c = Client(tmp_path, excel_file)
    yield c
    c.db.close()


async def fill_until_confirm(c, name="TESTOV ALPHA", phone="901112233", passport="TT1111111"):
    await c.press("reg:start")
    await c.text(name)
    await c.text(phone)
    return await c.text(passport)


# TEST 1
async def test_start_shows_welcome_with_register_button(client):
    out = await client.text("/start")
    assert out[0].startswith("Assalomu alaykum! 👋")
    button = client.last_markup().inline_keyboard[0][0]
    assert button.text == "📝 Ro‘yxatdan o‘tish" and button.callback_data == "reg:start"


# TEST 2-10 + 11: to'liq jarayon
async def test_full_registration_flow(client):
    await client.text("/start")
    out = await client.press("reg:start")
    assert out[0].startswith("1️⃣ Ism va familiyangizni")

    assert (await client.text("АЛИЕВ ВАЛИ"))[0].startswith("❌ Ism va familiya")      # TEST 3
    assert (await client.text("ALIYEV123 VALI"))[0].startswith("❌ Ism va familiya")  # TEST 4
    assert await client.state() == "Registration:waiting_name"

    out = await client.text("testov   alpha")                                         # TEST 2
    assert out[0].startswith("2️⃣ Telefon raqamingizni")
    assert client.last_markup().keyboard[0][0].request_contact is True

    assert (await client.text("+998901112233"))[0].startswith("❌ Telefon raqami")    # TEST 7
    assert (await client.text("12345"))[0].startswith("❌ Telefon raqami")            # TEST 8
    assert await client.state() == "Registration:waiting_phone"

    out = await client.text("901112233")                                              # TEST 5
    assert out[0].startswith("3️⃣ Pasport seriya")

    assert (await client.text("tt1111111"))[0].startswith("❌ Pasport")               # TEST 10
    assert (await client.text("TT 1111111"))[0].startswith("❌ Pasport")
    out = await client.text("TT1111111")                                              # TEST 9
    assert "👤 F.I.Sh.: TESTOV ALPHA" in out[0]
    assert "📱 Telefon: 998901112233" in out[0]
    assert "🪪 Pasport: TT1111111" in out[0]

    out = await client.press("reg:confirm")                                           # TEST 11
    assert out[0] == "🔎 Ma’lumotlaringiz tekshirilmoqda..."
    assert len(out) == 2
    result = out[1]
    assert result.startswith("🎓 Hurmatli TESTOV ALPHA BETA O‘G‘LI!\n\n")
    assert "🪪 TALABA ID: 300000000001\n" in result
    assert "🔑 Boshlang‘ich parol: TT1111111\n" in result
    assert "🌐 Sayt: https://student.kiu.uz\n" in result
    assert "👤 F.I.Sh.: TESTOV ALPHA BETA O‘G‘LI\n" in result
    assert "📚 Yo‘nalish: Test yo‘nalishi\n" in result
    assert result.endswith("Hurmat bilan,\nQarshi xalqaro universiteti ma’muriyati.")
    assert client.last_markup().inline_keyboard[0][0].url == "https://student.kiu.uz"
    assert await client.state() is None

    user = client.db.get_user(USER_ID)
    assert (user.hemis_id, user.phone, user.passport, user.username) == \
        ("300000000001", "998901112233", "TT1111111", "tester")


async def test_phone_accepted_with_998_prefix(client):                                # TEST 6
    await client.press("reg:start")
    await client.text("TESTOV ALPHA")
    out = await client.text("998901112233")
    assert out[0].startswith("3️⃣ Pasport")


async def test_contact_button(client):
    await client.press("reg:start")
    await client.text("TESTOV ALPHA")
    own = {"phone_number": "+998901112233", "first_name": "T", "user_id": USER_ID}
    foreign = {**own, "user_id": USER_ID + 1}
    assert (await client.message(contact=foreign))[0].startswith("❌ Iltimos, faqat o‘zingizning")
    out = await client.message(contact=own)
    assert out[0].startswith("3️⃣ Pasport")
    assert (await client.state()) == "Registration:waiting_passport"


async def test_not_found_gives_no_hemis_id(client):                                   # TEST 12
    out = await fill_until_confirm(client, passport="TT9999999")
    out = await client.press("reg:confirm")
    assert out[1].startswith("❌ Siz kiritgan ma’lumotlar bo‘yicha talaba topilmadi.")
    assert not any("HEMIS ID:" in t for t in out)
    assert client.db.get_user(USER_ID) is None


async def test_same_name_students(client):                                            # TEST 13
    await fill_until_confirm(client, "BIRXIL EPSILON", "905550002", "TQ4444444")
    out = await client.press("reg:confirm")
    assert "🪪 TALABA ID: 300000000004" in out[1]
    assert "📚 Yo‘nalish: —\n" in out[1]   # Excel'da yo'nalish bo'sh bo'lsa


async def test_start_during_registration_and_after(client):                           # TEST 14
    await client.press("reg:start")
    await client.text("TESTOV ALPHA")
    out = await client.text("/start")
    assert out[0].startswith("ℹ️ Ro‘yxatdan o‘tish jarayoni davom etmoqda")
    assert out[1].startswith("2️⃣ Telefon")
    assert await client.state() == "Registration:waiting_phone"

    await client.text("901112233")
    await client.text("TT1111111")
    await client.press("reg:confirm")
    out = await client.text("/start")
    assert out[0].startswith("ℹ️ Siz avval ro‘yxatdan o‘tgansiz.") and "300000000001" in out[0]


async def test_state_survives_restart(client):                                        # TEST 15
    await client.press("reg:start")
    await client.text("TESTOV ALPHA")
    await client.text("901112233")
    client.db.close()
    client.restart()
    assert await client.state() == "Registration:waiting_passport"
    out = await client.text("TT1111111")
    assert "📱 Telefon: 998901112233" in out[0]


async def test_cancel_button(client):                                                 # TEST 16
    await fill_until_confirm(client)
    out = await client.press("reg:cancel")
    assert out[0].startswith("❌ Ro‘yxatdan o‘tish bekor qilindi")
    assert await client.state() is None
    out = await client.press("reg:confirm")   # eski tugma endi ishlamaydi
    assert out == []
    assert client.db.get_user(USER_ID) is None


async def test_edit_button_restarts(client):
    await fill_until_confirm(client)
    out = await client.press("reg:edit")
    assert out[0].startswith("1️⃣ Ism va familiyangizni")
    assert await client.state() == "Registration:waiting_name"


async def test_reregister_button(client):                                             # TEST 17
    await fill_until_confirm(client)
    await client.press("reg:confirm")
    out = await client.press("reg:restart")
    assert out[0].startswith("1️⃣ Ism va familiyangizni")
    assert await client.state() == "Registration:waiting_name"
    await client.text("BIRXIL EPSILON")
    await client.text("905550001")
    await client.text("TQ3333333")
    out = await client.press("reg:confirm")
    assert "300000000003" in out[1]
    assert client.db.get_user(USER_ID).hemis_id == "300000000003"


async def test_non_text_inputs_do_not_crash(client):                                  # TEST 21-bo'lim
    await client.press("reg:start")
    sticker = {"file_id": "s", "file_unique_id": "s", "type": "regular", "width": 1, "height": 1,
               "is_animated": False, "is_video": False}
    for content in (
        {"photo": [{"file_id": "p", "file_unique_id": "p", "width": 1, "height": 1}]},
        {"sticker": sticker},
        {"voice": {"file_id": "v", "file_unique_id": "v", "duration": 1}},
        {"document": {"file_id": "d", "file_unique_id": "d"}},
    ):
        out = await client.message(**content)
        assert out == ["❌ Iltimos, ushbu bosqich uchun kerakli ma’lumotni matn ko‘rinishida yuboring."]
    assert await client.state() == "Registration:waiting_name"


async def test_excel_missing_keeps_confirmation(client, tmp_path):
    client.dp["registry"] = StudentRegistry(tmp_path / "yoq.xlsx")
    await fill_until_confirm(client)
    out = await client.press("reg:confirm")
    assert out[1].startswith("⚠️ Hozircha")
    assert await client.state() == "Registration:confirming_data"


async def test_web_api(excel_file):
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer

    bot_module.registry = StudentRegistry(excel_file)
    app = web.Application()
    app.router.add_get("/", bot_module.index_page)
    app.router.add_get("/api/check", bot_module.api_check)
    async with TestClient(TestServer(app)) as http:
        ok = await (await http.get("/api/check?passport=TT1111111&phone=901112233")).json()
        assert ok == {"found": True, "hemis_id": "300000000001", "full_name": "TESTOV ALPHA BETA O‘G‘LI"}
        only_passport = await (await http.get("/api/check?passport=TT1111111")).json()
        assert only_passport["found"] is False
        wrong = await (await http.get("/api/check?passport=TT1111111&phone=909999999")).json()
        assert wrong["found"] is False
        assert (await http.get("/")).status == 200


async def test_registration_is_sent_to_sheets(client):
    from tests.test_sheets_service import SECRET, FakeAppsScript
    from bot import SheetsSync

    fake = FakeAppsScript()
    await fake.server.start_server()
    sync = SheetsSync(client.db, fake.url, SECRET)
    client.dp["sheets"] = sync
    try:
        await fill_until_confirm(client)
        out = await client.press("reg:confirm")
        assert "300000000001" in out[1]
        for _ in range(50):
            if str(USER_ID) in fake.rows:
                break
            await asyncio.sleep(0.05)
        assert fake.rows[str(USER_ID)]["hemis_id"] == "300000000001"
    finally:
        client.dp["sheets"] = None
        await sync.stop()
        await fake.server.close()
