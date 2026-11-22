import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_tashkent_now_str() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Tashkent")).isoformat()
    except Exception:
        return datetime.now(timezone(timedelta(hours=5))).isoformat()

async def create_json_backup(db) -> str:
    """
    Ma'lumotlar bazasining to'liq JSON zaxira nusxasini tayyorlash.
    Ushbu nusxa SQLite yoki PostgreSQL bo'lishidan qat'i nazar
    barcha jadvallarni va statistikani o'z ichiga oladi.
    """
    now_str = get_tashkent_now_str()

    global_stats = await db.get_global_stats()
    active_contest = await db.get_active_contest()
    winners = await db.get_winners()
    suspicious = await db.get_suspicious_logs(limit=1000)
    admin_logs = await db.get_admin_logs(limit=1000)

    # Barcha foydalanuvchilar (tasdiqlangan va tasdiqlanmagan)
    all_users = []
    # Agar Postgres bo'lsa
    if hasattr(db, 'pool') and db.pool:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")
            all_users = [dict(r) for r in rows]
            ref_rows = await conn.fetch("SELECT * FROM referrals ORDER BY id DESC")
            all_referrals = [dict(r) for r in ref_rows]
    else:
        # SQLite
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            u_cur = await conn.execute("SELECT * FROM users ORDER BY created_at DESC")
            all_users = [dict(r) for r in await u_cur.fetchall()]
            r_cur = await conn.execute("SELECT * FROM referrals ORDER BY id DESC")
            all_referrals = [dict(r) for r in await r_cur.fetchall()]

    backup_data = {
        "project": "UniConnect UZ Telegram Bot",
        "backup_created_at": now_str,
        "global_stats": global_stats,
        "active_contest": active_contest,
        "total_users_count": len(all_users),
        "total_referrals_count": len(all_referrals),
        "users": all_users,
        "referrals": all_referrals,
        "winners": winners,
        "suspicious_logs": suspicious,
        "admin_logs": admin_logs
    }

    return json.dumps(backup_data, ensure_ascii=False, indent=2)
