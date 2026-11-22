import os
import config
from pathlib import Path
from typing import Optional, Union, Any

from database.sqlite_engine import (
    Database as SqliteDatabase,
    get_tashkent_now,
    make_tashkent_aware
)
from database.pg_engine import PostgresDatabase

class Database:
    """
    Dual-Engine Database Architecture:
    - Muhitda DATABASE_URL (PostgreSQL / Neon) mavjud bo'lsa -> PostgresDatabase (asyncpg pool)
    - Muhitda DATABASE_URL bo'lmasa -> SqliteDatabase (aiosqlite)
    Bu tizim orqali bot lokal muhitda ham, Render bulutida ham xatosiz va bir xil interfeysda ishlaydi.
    """
    def __new__(cls, db_path: Optional[Union[Path, str]] = None, database_url: Optional[str] = None, force_sqlite: bool = False) -> Any:
        # 1. Maxsus SQLite talab qilinganda (unit testlar uchun)
        if force_sqlite:
            target_path = db_path or config.DB_PATH
            return SqliteDatabase(db_path=target_path)

        # 2. Aniq parametr orqali database_url berilgan bo'lsa -> Postgres
        if database_url:
            return PostgresDatabase(database_url=database_url)

        # 3. Muhitda DATABASE_URL mavjud bo'lsa (Render / Neon) -> USTUVOR: POSTGRESQL!
        target_url = config.DATABASE_URL
        if target_url and (target_url.startswith("postgresql://") or target_url.startswith("postgres://")):
            return PostgresDatabase(database_url=target_url)

        # 4. DATABASE_URL bo'lmaganida -> SQLite
        target_path = db_path or config.DB_PATH
        return SqliteDatabase(db_path=target_path)

__all__ = ["Database", "SqliteDatabase", "PostgresDatabase", "get_tashkent_now", "make_tashkent_aware"]
