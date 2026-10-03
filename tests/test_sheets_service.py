import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from bot import Database
from bot import SheetsSync, create_sheets_sync

SECRET = "test-secret"


class FakeAppsScript:
    """Google Apps Script Web App'ga o'xshaydi: POST -> 302 redirect -> GET javob."""

    def __init__(self):
        self.rows: dict[str, list] = {}
        self.fail = False
        self._last = None
        app = web.Application()
        app.router.add_post("/exec", self.exec_)
        app.router.add_get("/echo", self.echo)
        self.server = TestServer(app)

    async def exec_(self, request):
        if self.fail:
            return web.Response(status=500)
        body = await request.json()
        if body.get("secret") != SECRET:
            self._last = {"ok": False, "error": "unauthorized"}
        else:
            r = body["record"]
            self.rows[r["telegram_id"]] = r
            self._last = {"ok": True}
        raise web.HTTPFound("/echo")

    async def echo(self, request):
        return web.json_response(self._last)

    @property
    def url(self):
        return str(self.server.make_url("/exec"))


@pytest.fixture
async def apps_script():
    fake = FakeAppsScript()
    await fake.server.start_server()
    yield fake
    await fake.server.close()


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "s.db")
    yield d
    d.close()


def add_user(db, telegram_id=1, hemis="300000000001"):
    db.save_user(telegram_id, "tester", "TESTOV ALPHA", "998901112233", "TT1111111", hemis)


async def test_sync_writes_and_marks(db, apps_script):
    add_user(db)
    sync = SheetsSync(db, apps_script.url, SECRET)
    assert await sync.sync_pending() == 1
    row = apps_script.rows["1"]
    assert (row["full_name"], row["phone"], row["passport"], row["hemis_id"], row["username"]) == \
        ("TESTOV ALPHA", "998901112233", "TT1111111", "300000000001", "tester")
    assert len(row["registered_at"]) == 19  # Toshkent vaqti: YYYY-MM-DD HH:MM:SS
    assert db.get_unsynced_users() == []
    assert await sync.sync_pending() == 0  # qayta yuborilmaydi
    await sync.stop()


async def test_failure_is_retried_later(db, apps_script):
    add_user(db)
    sync = SheetsSync(db, apps_script.url, SECRET)
    apps_script.fail = True
    assert await sync.sync_pending() == 0
    assert len(db.get_unsynced_users()) == 1   # yo'qolmaydi
    apps_script.fail = False
    assert await sync.sync_pending() == 1
    await sync.stop()


async def test_wrong_secret_not_marked(db, apps_script):
    add_user(db)
    sync = SheetsSync(db, apps_script.url, "boshqa-kalit")
    assert await sync.sync_pending() == 0
    assert apps_script.rows == {}
    assert len(db.get_unsynced_users()) == 1
    await sync.stop()


async def test_unreachable_server(db):
    add_user(db)
    sync = SheetsSync(db, "http://127.0.0.1:9/exec", SECRET)
    assert await sync.sync_pending() == 0
    assert len(db.get_unsynced_users()) == 1
    await sync.stop()


async def test_reregistration_is_sent_again(db, apps_script):
    add_user(db)
    sync = SheetsSync(db, apps_script.url, SECRET)
    await sync.sync_pending()
    await asyncio.sleep(1.1)  # registered_at soniya aniqligida
    add_user(db, hemis="300000000004")
    assert await sync.sync_pending() == 1
    assert apps_script.rows["1"]["hemis_id"] == "300000000004"
    await sync.stop()


def test_disabled_without_url_or_secret(db):
    assert create_sheets_sync(db, "", SECRET, 60) is None
    assert create_sheets_sync(db, "https://example.invalid/exec", "", 60) is None
    assert create_sheets_sync(db, "https://example.invalid/exec", SECRET, 60) is not None


def test_existing_database_is_migrated(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE users (telegram_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT NOT NULL,"
                 " phone TEXT NOT NULL, passport TEXT NOT NULL, hemis_id TEXT NOT NULL, registered_at TEXT NOT NULL)")
    conn.execute("INSERT INTO users VALUES (7, NULL, 'ESKI USER', '998900000000', 'TE0000000', '1', "
                 "'2026-01-01T00:00:00+00:00')")
    conn.commit()
    conn.close()
    d = Database(path)
    assert [u.telegram_id for u in d.get_unsynced_users()] == [7]  # eski yozuvlar ham yuboriladi
    d.close()


async def test_both_phones_are_sent(db, apps_script):
    db.save_user(5, None, "IKKI TELEFON", "998935550000", "TT1111111", "300000000005", "998901112233")
    db.save_user(6, None, "BIR TELEFON", "998935550001", "TT1111112", "300000000006", "998935550001")
    sync = SheetsSync(db, apps_script.url, SECRET)
    assert await sync.sync_pending() == 2
    assert apps_script.rows["5"]["phone"] == "998935550000 / 998901112233"
    assert apps_script.rows["6"]["phone"] == "998935550001 / 998935550001"   # bir xil bo'lsa ham ikkalasi
    await sync.stop()
