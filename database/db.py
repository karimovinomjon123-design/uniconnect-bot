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
    def __new__(cls, db_path: Optional[Union[Path, str]] = None, database_url: Optional[str] = None) -> Any:
        if database_url:
            return PostgresDatabase(database_url=database_url)
        if db_path:
            return SqliteDatabase(db_path=db_path)
        if config.DATABASE_URL and (config.DATABASE_URL.startswith("postgresql://") or config.DATABASE_URL.startswith("postgres://")):
            return PostgresDatabase(database_url=config.DATABASE_URL)
        return SqliteDatabase(db_path=config.DB_PATH)

__all__ = ["Database", "SqliteDatabase", "PostgresDatabase", "get_tashkent_now", "make_tashkent_aware"]
