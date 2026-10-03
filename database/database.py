"""SQLite ma'lumotlar bazasi: ro'yxatdan o'tganlar va ro'yxatdan o'tish holati (FSM).

FSM holati bazada saqlangani uchun bot qayta ishga tushsa ham foydalanuvchi
qaysi bosqichda ekanligi yo'qolmaydi.
"""
import json
import sqlite3
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_id   INTEGER PRIMARY KEY,
    username      TEXT,
    full_name     TEXT NOT NULL,
    phone         TEXT NOT NULL,
    passport      TEXT NOT NULL,
    hemis_id      TEXT NOT NULL,
    registered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fsm (
    storage_key TEXT PRIMARY KEY,
    state       TEXT,
    data        TEXT NOT NULL DEFAULT '{}'
);
"""


@dataclass(frozen=True)
class RegisteredUser:
    telegram_id: int
    username: str | None
    full_name: str
    phone: str
    passport: str
    hemis_id: str
    registered_at: str


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
            self._conn.commit()
            return rows

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---------------- Ro'yxatdan o'tganlar ----------------

    def save_user(self, telegram_id: int, username: str | None, full_name: str,
                  phone: str, passport: str, hemis_id: str) -> None:
        self.execute(
            """
            INSERT INTO users (telegram_id, username, full_name, phone, passport, hemis_id, registered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                phone = excluded.phone,
                passport = excluded.passport,
                hemis_id = excluded.hemis_id,
                registered_at = excluded.registered_at
            """,
            (telegram_id, username, full_name, phone, passport, hemis_id,
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )

    def get_user(self, telegram_id: int) -> RegisteredUser | None:
        rows = self.execute(
            "SELECT telegram_id, username, full_name, phone, passport, hemis_id, registered_at "
            "FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        return RegisteredUser(*rows[0]) if rows else None


def _key(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id or ''}:{key.destiny}"


class SQLiteStorage(BaseStorage):
    """aiogram FSM holatini SQLite bazada saqlaydi."""

    def __init__(self, db: Database):
        self.db = db

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if isinstance(state, State) else state
        self.db.execute(
            "INSERT INTO fsm (storage_key, state) VALUES (?, ?) "
            "ON CONFLICT(storage_key) DO UPDATE SET state = excluded.state",
            (_key(key), value),
        )

    async def get_state(self, key: StorageKey) -> str | None:
        rows = self.db.execute("SELECT state FROM fsm WHERE storage_key = ?", (_key(key),))
        return rows[0][0] if rows else None

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        self.db.execute(
            "INSERT INTO fsm (storage_key, data) VALUES (?, ?) "
            "ON CONFLICT(storage_key) DO UPDATE SET data = excluded.data",
            (_key(key), json.dumps(dict(data), ensure_ascii=False)),
        )

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        rows = self.db.execute("SELECT data FROM fsm WHERE storage_key = ?", (_key(key),))
        return json.loads(rows[0][0]) if rows else {}

    async def close(self) -> None:
        pass
