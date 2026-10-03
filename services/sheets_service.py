"""Ro'yxatdan o'tganlarni Google Sheets'ga yozish (Google Apps Script Web App orqali).

Ma'lumot avval SQLite bazaga yoziladi, keyin Sheets'ga yuboriladi. Yuborib bo'lmasa
(internet, Google xatoligi), fon vazifasi uni keyinroq qayta yuboradi.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp

from database.database import Database, RegisteredUser

logger = logging.getLogger(__name__)

# O'zbekiston vaqti (UTC+5, yozgi vaqt yo'q)
TASHKENT_TZ = timezone(timedelta(hours=5))
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


def local_time(iso_utc: str) -> str:
    try:
        return datetime.fromisoformat(iso_utc).astimezone(TASHKENT_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_utc


def build_record(user: RegisteredUser) -> dict:
    return {
        "telegram_id": str(user.telegram_id),
        "username": user.username or "",
        "full_name": user.full_name,
        "phone": user.phone,
        "passport": user.passport,
        "hemis_id": user.hemis_id,
        "registered_at": local_time(user.registered_at),
    }


class SheetsSync:
    def __init__(self, db: Database, url: str, secret: str, interval: int = 60):
        self.db = db
        self.url = url
        self.secret = secret
        self.interval = max(10, interval)
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._triggers: set[asyncio.Task] = set()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)
        return self._session

    async def push(self, user: RegisteredUser) -> bool:
        """Bitta foydalanuvchini Sheets'ga yozadi. Muvaffaqiyatli bo'lsa True."""
        session = await self._get_session()
        payload = {"secret": self.secret, "record": build_record(user)}
        try:
            async with session.post(self.url, json=payload) as resp:
                if resp.status != 200:
                    logger.warning("Sheets javobi %s (user_id=%s)", resp.status, user.telegram_id)
                    return False
                body = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
            logger.warning("Sheets'ga yozib bo'lmadi (user_id=%s): %s", user.telegram_id, type(e).__name__)
            return False
        if not isinstance(body, dict) or body.get("ok") is not True:
            error = body.get("error") if isinstance(body, dict) else None
            logger.warning("Sheets xatolik qaytardi (user_id=%s): %s", user.telegram_id, error)
            return False
        return True

    async def sync_pending(self) -> int:
        """Yozilmagan barcha foydalanuvchilarni yuboradi. Yuborilganlar sonini qaytaradi."""
        async with self._lock:
            sent = 0
            users = await asyncio.to_thread(self.db.get_unsynced_users)
            for user in users:
                if not await self.push(user):
                    break  # Sheets ishlamayapti -- keyingi urinishda davom etamiz
                await asyncio.to_thread(self.db.mark_synced, user)
                sent += 1
            if sent:
                logger.info("Google Sheets'ga %d ta yozuv yuborildi", sent)
            return sent

    def trigger(self) -> None:
        """Yangi ro'yxatdan o'tgandan keyin darhol yuborish (javobni kutmasdan)."""
        task = asyncio.create_task(self._safe_sync())
        self._triggers.add(task)
        task.add_done_callback(self._triggers.discard)

    async def _safe_sync(self) -> None:
        try:
            await self.sync_pending()
        except Exception:
            logger.exception("Google Sheets bilan sinxronlashda kutilmagan xatolik")

    async def _run_forever(self) -> None:
        while True:
            await self._safe_sync()
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        for task in (self._task, *self._triggers):
            if task and not task.done():
                task.cancel()
        self._task = None
        if self._session and not self._session.closed:
            await self._session.close()


def create_sheets_sync(db: Database, url: str, secret: str, interval: int) -> SheetsSync | None:
    if not url:
        return None
    if not secret:
        logger.error("SHEETS_WEBHOOK_URL berilgan, lekin SHEETS_SECRET bo'sh -- Google Sheets o'chirildi")
        return None
    return SheetsSync(db, url, secret, interval)
