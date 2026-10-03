"""Botning to'liq ro'yxatdan o'tish jarayoni (Telegram API soxtalashtirilgan)."""
import asyncio
import itertools
from datetime import datetime

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import AnswerCallbackQuery, CopyMessage, EditMessageReplyMarkup, GetChatMember, SendMessage
from aiogram.types import Chat, ChatMemberLeft, ChatMemberMember, Message, MessageId, Update, User

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
        self.channel_member = True   # majburiy kanalga a'zomi (GetChatMember javobi)
        self.blocked: set[int] = set()   # botni bloklagan foydalanuvchilar

    async def make_request(self, bot, method, timeout=None):
        self.sent.append(method)
        if getattr(method, "chat_id", None) in self.blocked:
            raise TelegramForbiddenError(method=method, message="Forbidden: bot was blocked by the user")
        if isinstance(method, CopyMessage):
            return MessageId(message_id=next(_ids))
        if isinstance(method, (AnswerCallbackQuery, EditMessageReplyMarkup)):
            return True
        if isinstance(method, GetChatMember):
            user = User(id=method.user_id, is_bot=False, first_name="T")
            return ChatMemberMember(user=user) if self.channel_member else ChatMemberLeft(user=user)
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


SHARED = "+998935550000"   # Telegram orqali yuboriladigan (share) raqam -- test uchun


async def share(c, phone=SHARED, user_id=USER_ID):
    return await c.message(contact={"phone_number": phone, "first_name": "T", "user_id": user_id})


async def fill_until_confirm(c, name="TESTOV ALPHA", phone="901112233", passport="TT1111111"):
    await c.press("reg:start")
    await c.text(name)
    await share(c)
    await c.text(phone)
    return await c.text(passport)


# TEST 1
async def test_start_shows_welcome_with_register_button(client):
    out = await client.text("/start")
    assert out[0].startswith("Assalomu alaykum!\nQarshi xalqaro universiteti")
    button = client.last_markup().inline_keyboard[0][0]
    assert button.text == "📝 Ro‘yxatdan o‘tish" and button.callback_data == "reg:start"


# TEST 2-10 + 11: to'liq jarayon
async def test_full_registration_flow(client):
    await client.text("/start")
    out = await client.press("reg:start")
    assert out[0].startswith("Ism va familiyangizni")

    assert (await client.text("АЛИЕВ ВАЛИ"))[0].startswith("❌ Ism va familiya")      # TEST 3
    assert (await client.text("ALIYEV123 VALI"))[0].startswith("❌ Ism va familiya")  # TEST 4
    assert await client.state() == "Registration:waiting_name"

    out = await client.text("testov   alpha")                                         # TEST 2
    assert out == ["«Telefon raqamni yuborish» tugmasini bosing."]
    assert client.last_markup().keyboard[0][0].request_contact is True

    # Tugma bosqichida raqamni yozib yuborish mumkin emas
    assert (await client.text("901112233"))[0].startswith("❌ Iltimos, pastdagi «📱 Telefon")
    assert await client.state() == "Registration:waiting_phone"

    out = await share(client)
    assert out[0].startswith("Telefon raqamingizni yuboring.")
    assert await client.state() == "Registration:waiting_phone2"

    assert (await client.text("+998901112233"))[0].startswith("❌ Telefon raqami")    # TEST 7
    assert (await client.text("12345"))[0].startswith("❌ Telefon raqami")            # TEST 8
    assert await client.state() == "Registration:waiting_phone2"

    out = await client.text("901112233")                                              # TEST 5
    assert out[0].startswith("Pasport seriya")

    assert (await client.text("tt1111111"))[0].startswith("❌ Pasport")               # TEST 10
    assert (await client.text("TT 1111111"))[0].startswith("❌ Pasport")
    out = await client.text("TT1111111")                                              # TEST 9
    assert out[0] == (
        "🔎 Kiritilgan ma’lumotlaringiz:\n"
        "👤 F.I.Sh.: TESTOV ALPHA\n"
        "📱 Telefon: 998935550000\n"
        "📞 Qo‘shimcha telefon: 998901112233\n"
        "🪪 Pasport: TT1111111\n\n"
        "Ma’lumotlaringizni tasdiqlaysizmi?"
    )

    out = await client.press("reg:confirm")                                           # TEST 11
    assert out[0] == "🔎 Ma’lumotlaringiz tekshirilmoqda..."
    assert len(out) == 2
    result = out[1]
    assert result.startswith("Hurmatli TESTOV ALPHA BETA O‘G‘LI!\n\n")
    assert "🪪 TALABA ID: 300000000001\n" in result
    assert "🔑 Boshlang‘ich parol: TT1111111\n" in result
    assert "🌐 Sayt: https://student.kiu.uz\n" in result
    assert "👤 F.I.Sh.: TESTOV ALPHA BETA O‘G‘LI\n" in result
    assert "📚 Yo‘nalish: Test yo‘nalishi\n" in result
    assert result.endswith("parolingizni albatta almashtiring.")
    assert client.last_markup().inline_keyboard[0][0].url == "https://student.kiu.uz"
    assert await client.state() is None

    user = client.db.get_user(USER_ID)
    assert (user.hemis_id, user.phone, user.phone2, user.passport, user.username) == \
        ("300000000001", "998935550000", "998901112233", "TT1111111", "tester")


async def test_phone_accepted_with_998_prefix(client):                                # TEST 6
    await client.press("reg:start")
    await client.text("TESTOV ALPHA")
    await share(client)
    out = await client.text("998901112233")
    assert out[0].startswith("Pasport")


async def test_contact_button(client):
    await client.press("reg:start")
    await client.text("TESTOV ALPHA")
    out = await share(client, user_id=USER_ID + 1)          # boshqa odamning kontakti
    assert out[0].startswith("❌ Iltimos, faqat o‘zingizning")
    assert await client.state() == "Registration:waiting_phone"
    out = await share(client, phone="+7 999 123 45 67")    # chet el raqami ham qabul qilinadi
    assert out[0].startswith("Telefon raqamingizni yuboring.")
    assert (await client.state()) == "Registration:waiting_phone2"
    # Qo'lda kiritish bosqichida kontakt emas, matn kutiladi
    out = await share(client)
    assert out == ["❌ Iltimos, ushbu bosqich uchun kerakli ma’lumotni matn ko‘rinishida yuboring."]
    await client.text("901112233")
    out = await client.text("TT1111111")
    assert "📱 Telefon: +79991234567" in out[0]


async def test_not_found_gives_no_hemis_id(client):                                   # TEST 12
    out = await fill_until_confirm(client, passport="TT9999999")
    out = await client.press("reg:confirm")
    assert out[1].startswith("❌ Siz kiritgan ma’lumotlar bo‘yicha talaba topilmadi.")
    assert not any("TALABA ID" in t for t in out)
    # Urinish saqlanadi (Google Sheets uchun), lekin HEMIS ID berilmaydi
    user = client.db.get_user(USER_ID)
    assert (user.hemis_id, user.passport) == ("TOPILMADI", "TT9999999")
    # /start -- bosh menyu, qayta urinish mumkin
    out = await client.text("/start")
    assert out[0].startswith("Assalomu alaykum!")
    out = await client.press("reg:restart")
    assert out[0].startswith("Ism va familiyangizni")
    await client.text("TESTOV ALPHA")
    await share(client)
    await client.text("901112233")
    await client.text("TT1111111")
    out = await client.press("reg:confirm")
    assert "🪪 TALABA ID: 300000000001" in out[1]
    assert client.db.get_user(USER_ID).hemis_id == "300000000001"


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
    assert out[1].startswith("«Telefon raqamni yuborish»")
    assert await client.state() == "Registration:waiting_phone"
    assert client.last_markup().keyboard[0][0].request_contact is True

    await share(client)
    out = await client.text("/start")
    assert out[1].startswith("Telefon raqamingizni yuboring.")
    await client.text("901112233")
    await client.text("TT1111111")
    await client.press("reg:confirm")
    out = await client.text("/start")
    assert out[0].startswith("ℹ️ Siz avval ro‘yxatdan o‘tgansiz.") and "300000000001" in out[0]


async def test_state_survives_restart(client):                                        # TEST 15
    await client.press("reg:start")
    await client.text("TESTOV ALPHA")
    await share(client)
    await client.text("901112233")
    client.db.close()
    client.restart()
    assert await client.state() == "Registration:waiting_passport"
    out = await client.text("TT1111111")
    assert "📱 Telefon: 998935550000" in out[0]
    assert "📞 Qo‘shimcha telefon: 998901112233" in out[0]


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
    assert out[0].startswith("Ism va familiyangizni")
    assert await client.state() == "Registration:waiting_name"


async def test_one_hemis_id_per_account(client):                                     # TEST 17
    await fill_until_confirm(client)
    out = await client.press("reg:confirm")
    # Natijada "Qayta ro'yxatdan o'tish" tugmasi yo'q -- faqat sayt
    assert [b.callback_data for row in client.last_markup().inline_keyboard for b in row] == [None]
    # Eski tugma yoki /start orqali boshqa pasportni tekshirib bo'lmaydi
    out = await client.press("reg:restart")
    assert out[0].startswith("ℹ️ Siz avval ro‘yxatdan o‘tgansiz.") and "300000000001" in out[0]
    assert await client.state() is None
    out = await client.press("reg:start")
    assert "300000000001" in out[0]
    out = await client.text("/start")
    assert out[0].startswith("ℹ️ Siz avval ro‘yxatdan o‘tgansiz.")
    assert client.db.get_user(USER_ID).hemis_id == "300000000001"


async def test_one_id_enforced_even_at_confirmation(client):
    # Ro'yxatdan o'tish boshlangan, shu orada (boshqa oynadan) HEMIS ID olingan
    await fill_until_confirm(client, "BIRXIL EPSILON", "905550001", "TQ3333333")
    client.db.save_user(USER_ID, "tester", "TESTOV ALPHA", "998935550000", "TT1111111", "300000000001")
    out = await client.press("reg:confirm")
    assert out[0].startswith("ℹ️ Bitta Telegram akkauntdan faqat bitta HEMIS ID")
    assert client.db.get_user(USER_ID).hemis_id == "300000000001"


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
        wrong_phone = await (await http.get("/api/check?passport=TT1111111&phone=909999999")).json()
        assert wrong_phone["hemis_id"] == "300000000001"   # pasport to'g'ri bo'lsa yetarli
        unknown = await (await http.get("/api/check?passport=TT9999999&phone=901112233")).json()
        assert unknown["found"] is False
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


async def test_wrong_name_but_correct_passport(client):
    await fill_until_confirm(client, name="NOTOGRI ISM", phone="909999999", passport="TT1111111")
    out = await client.press("reg:confirm")
    # Bazaga talaba yozgan xato ism emas, ro'yxatdagi to'g'ri ism saqlanadi
    assert client.db.get_user(USER_ID).full_name == "TESTOV ALPHA BETA O'G'LI"
    # Salomlashuvda bazadagi to'g'ri ism ishlatiladi
    assert out[1].startswith("Hurmatli TESTOV ALPHA BETA O‘G‘LI!")
    assert "🪪 TALABA ID: 300000000001" in out[1]


@pytest.fixture
def required_channel(monkeypatch):
    monkeypatch.setattr(bot_module, "REQUIRED_CHANNEL", "@test_kanal")
    monkeypatch.setattr(bot_module, "REQUIRED_CHANNEL_URL", "https://t.me/test_kanal")
    bot_module._subscribed_until.clear()
    yield
    bot_module._subscribed_until.clear()


async def test_channel_subscription_required(client, required_channel):
    client.session.channel_member = False
    out = await client.text("/start")
    assert out == [bot_module.SUBSCRIBE_REQUIRED]
    buttons = client.last_markup().inline_keyboard
    assert buttons[0][0].url == "https://t.me/test_kanal"
    assert buttons[1][0].callback_data == "sub:check"
    # Ro'yxatdan o'tish tugmasi ham ishlamaydi
    out = await client.press("reg:start")
    assert out == [bot_module.SUBSCRIBE_REQUIRED]
    assert await client.state() is None
    # A'zo bo'lmay "Tekshirish" bosilsa -- ogohlantirish (yangi xabar yo'q)
    assert await client.press("sub:check") == []

    # A'zo bo'lgach -- bosh menyu chiqadi va bot odatdagidek ishlaydi
    client.session.channel_member = True
    out = await client.press("sub:check")
    assert out[0].startswith("Assalomu alaykum!")
    await fill_until_confirm(client)
    out = await client.press("reg:confirm")
    assert "🪪 TALABA ID: 300000000001" in out[1]


async def test_channel_check_resumes_registration_step(client, required_channel):
    await client.press("reg:start")           # a'zo -- ism bosqichi
    client.session.channel_member = False
    bot_module._subscribed_until.clear()      # kanaldan chiqib ketdi
    out = await client.text("TESTOV ALPHA")
    assert out == [bot_module.SUBSCRIBE_REQUIRED]
    assert await client.state() == "Registration:waiting_name"
    client.session.channel_member = True
    out = await client.press("sub:check")
    assert out[0].startswith("Ism va familiyangizni")


async def test_channel_check_can_be_turned_off(client):
    assert bot_module.REQUIRED_CHANNEL == ""   # REQUIRED_CHANNEL=off
    client.session.channel_member = False
    out = await client.text("/start")
    assert out[0].startswith("Assalomu alaykum!")


# ---------------- Rassilka ----------------

@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setattr(bot_module, "ADMIN_IDS", {USER_ID})
    monkeypatch.setattr(bot_module, "BROADCAST_DELAY", 0)


def add_students(db):
    db.save_user(2001, None, "ALIYEV VALI SOBIROVICH", "998900000001", "TA0000001", "300000000011")
    db.save_user(2002, None, "KARIMOVA DILNOZA", "998900000002", "TA0000002", "300000000012")
    db.save_user(2003, None, "TOPILMAGAN TALABA", "998900000003", "TA0000003", "TOPILMADI")


async def finish_broadcasts():
    await asyncio.gather(*list(bot_module._broadcast_tasks))


def sent_to(client, chat_id):
    return [m for m in client.session.sent if getattr(m, "chat_id", None) == chat_id
            and isinstance(m, (SendMessage, CopyMessage))]


async def test_broadcast_with_names(client, admin):
    add_students(client.db)
    client.session.blocked.add(2002)
    out = await client.text("/rassilka")
    assert out[0].startswith("📨 Rassilka xabarini yuboring.")
    out = await client.text("Hurmatli {ism}! ({fio}) Ertaga dars bor.")
    assert out[0].startswith("👀")
    assert out[1] == "Hurmatli Vali! (ALIYEV VALI SOBIROVICH) Ertaga dars bor."
    buttons = [b.text for row in client.last_markup().inline_keyboard for b in row]
    assert buttons == ["📢 Hammaga (3)", "✅ HEMIS ID olganlarga (2)", "❌ Topilmaganlarga (1)", "🚫 Bekor qilish"]

    out = await client.press("bc:hemis")
    assert out == ["⏳ Rassilka boshlandi: 2 ta qabul qiluvchi."]
    await finish_broadcasts()
    assert [m.text for m in sent_to(client, 2001)] == ["Hurmatli Vali! (ALIYEV VALI SOBIROVICH) Ertaga dars bor."]
    assert sent_to(client, 2003) == []                       # topilmaganlarga yuborilmadi
    report = [m.text for m in sent_to(client, USER_ID) if m.text and m.text.startswith("✅ Rassilka tugadi")]
    assert report and "Yuborildi: 1" in report[0] and "Yuborilmadi: 1" in report[0]
    assert await client.state() is None


async def test_broadcast_photo_to_not_found(client, admin):
    add_students(client.db)
    await client.text("/rassilka")
    out = await client.message(photo=[{"file_id": "p", "file_unique_id": "p", "width": 1, "height": 1}],
                               caption="{ism}, ma’lumotlaringizni tekshiring")
    await client.press("bc:nf")
    await finish_broadcasts()
    copies = [m for m in sent_to(client, 2003) if isinstance(m, CopyMessage)]
    assert len(copies) == 1 and copies[0].caption == "Talaba, ma’lumotlaringizni tekshiring"
    assert sent_to(client, 2001) == []


async def test_broadcast_cancel_and_commands(client, admin):
    add_students(client.db)
    await client.text("/rassilka")
    out = await client.text("/bekor")
    assert out == ["🚫 Rassilka bekor qilindi."]
    await client.text("/rassilka")
    await client.text("Salom {ism}")
    out = await client.press("bc:cancel")
    assert out == ["🚫 Rassilka bekor qilindi."]
    await finish_broadcasts()
    assert sent_to(client, 2001) == []


async def test_broadcast_only_for_admins(client):
    add_students(client.db)
    out = await client.text("/rassilka")
    assert not any("Rassilka" in t for t in out)          # oddiy foydalanuvchiga ishlamaydi
    assert await client.press("bc:all") == []
    await finish_broadcasts()
    assert sent_to(client, 2001) == []
    out = await client.text("/id")
    assert out == [f"Sizning Telegram ID raqamingiz: {USER_ID}"]


async def test_broadcast_includes_sheets_rows(client, admin):
    from tests.test_sheets_service import SECRET, FakeAppsScript
    from bot import SheetsSync

    fake = FakeAppsScript()
    fake.rows["3001"] = {"telegram_id": "3001", "full_name": "SHEETSDAGI TALABA", "hemis_id": "300000000031"}
    fake.rows["TEST"] = {"telegram_id": "TEST", "full_name": "SINOV", "hemis_id": "TEST"}
    await fake.server.start_server()
    sync = SheetsSync(client.db, fake.url, SECRET)
    client.dp["sheets"] = sync
    try:
        add_students(client.db)
        await client.text("/rassilka")
        out = await client.text("Salom {ism}")
        assert out[2].startswith("Qabul qiluvchilar manbasi: bot bazasi va Google Sheets")
        await client.press("bc:all")
        await finish_broadcasts()
        assert [m.text for m in sent_to(client, 3001)] == ["Salom Talaba"]
    finally:
        client.dp["sheets"] = None
        await sync.stop()
        await fake.server.close()
