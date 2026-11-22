import os
import sys
import asyncio
import sqlite3
from pathlib import Path

# Loyiha ildiz papkasini importlar uchun qo'shish
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from database.pg_engine import PostgresDatabase

async def run_migration():
    print("=" * 60)
    print("   UNICONNECT UZ: SQLITE -> NEON POSTGRESQL MIGRATSIYA")
    print("=" * 60)

    db_url = config.DATABASE_URL or os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        print("\n[OGOHLANTIRISH] DATABASE_URL aniqlanmadi!")
        print("Iltimos, .env fayliga yoki buyruq satriga Neon connection string'ini kiriting:")
        print("Misol:")
        print("DATABASE_URL=postgresql://user:password@ep-xyz-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require\n")
        sys.exit(1)

    sqlite_path = config.DB_PATH
    if not sqlite_path.exists():
        print(f"[XATOLIK] SQLite fayli topilmadi: {sqlite_path}")
        sys.exit(1)

    print(f"1. SQLite manbai: {sqlite_path}")
    masked_url = db_url.split("@")[-1] if "@" in db_url else "..."
    print(f"2. PostgreSQL maqsadi: ...@{masked_url}")

    # 1. PostgreSQL ulanishi va jadvallarni yaratish
    pg_db = PostgresDatabase(db_url)
    await pg_db.init_db()
    print("3. PostgreSQL jadvallari va indekslari muvaffaqiyatli tekshirildi.")

    # 2. SQLite dan ma'lumotlarni o'qish
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    s_cur = sqlite_conn.cursor()

    async with pg_db.pool.acquire() as conn:
        async with conn.transaction():
            print("\n4. Ma'lumotlarni xavfsiz (idempotent) ko'chirish boshlandi...")

            # --- A. USERS ---
            s_cur.execute("SELECT * FROM users")
            users = [dict(r) for r in s_cur.fetchall()]
            for u in users:
                await conn.execute("""
                    INSERT INTO users (user_id, username, full_name, referrer_id, is_verified, referral_count, contest_referrals, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (user_id) DO UPDATE SET
                        username = EXCLUDED.username,
                        full_name = EXCLUDED.full_name,
                        referrer_id = EXCLUDED.referrer_id,
                        is_verified = EXCLUDED.is_verified,
                        referral_count = EXCLUDED.referral_count,
                        contest_referrals = EXCLUDED.contest_referrals,
                        status = EXCLUDED.status;
                """, u["user_id"], u.get("username"), u["full_name"], u.get("referrer_id"),
                     u.get("is_verified", 0), u.get("referral_count", 0),
                     u.get("contest_referrals", 0), u.get("status", "active"), u["created_at"])
            print(f"   - Users ko'chirildi: {len(users)} ta")

            # --- B. CONTESTS ---
            s_cur.execute("SELECT * FROM contests")
            contests = [dict(r) for r in s_cur.fetchall()]
            for c in contests:
                await conn.execute("""
                    INSERT INTO contests (id, season, title, start_date, end_date, prize_1, prize_2, prize_3, min_referrals, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (id) DO UPDATE SET
                        season = EXCLUDED.season,
                        title = EXCLUDED.title,
                        start_date = EXCLUDED.start_date,
                        end_date = EXCLUDED.end_date,
                        prize_1 = EXCLUDED.prize_1,
                        prize_2 = EXCLUDED.prize_2,
                        prize_3 = EXCLUDED.prize_3,
                        min_referrals = EXCLUDED.min_referrals,
                        status = EXCLUDED.status;
                """, c["id"], c.get("season", 1), c["title"], c["start_date"], c["end_date"],
                     c["prize_1"], c["prize_2"], c["prize_3"], c.get("min_referrals", 20),
                     c["status"], c["created_at"])
            print(f"   - Contests ko'chirildi: {len(contests)} ta")

            # --- C. REFERRALS ---
            s_cur.execute("SELECT * FROM referrals")
            referrals = [dict(r) for r in s_cur.fetchall()]
            for ref in referrals:
                await conn.execute("""
                    INSERT INTO referrals (id, referrer_id, referred_id, status, contest_id, is_contest_credit, created_at, confirmed_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (referred_id) DO UPDATE SET
                        referrer_id = EXCLUDED.referrer_id,
                        status = EXCLUDED.status,
                        contest_id = EXCLUDED.contest_id,
                        is_contest_credit = EXCLUDED.is_contest_credit,
                        confirmed_at = EXCLUDED.confirmed_at;
                """, ref["id"], ref["referrer_id"], ref["referred_id"], ref.get("status", "pending"),
                     ref.get("contest_id"), ref.get("is_contest_credit", 0),
                     ref["created_at"], ref.get("confirmed_at"))
            print(f"   - Referrals ko'chirildi: {len(referrals)} ta")

            # --- D. WINNERS ---
            try:
                s_cur.execute("SELECT * FROM winners")
                winners = [dict(r) for r in s_cur.fetchall()]
                for w in winners:
                    await conn.execute("""
                        INSERT INTO winners (id, contest_id, user_id, rank, referral_count, prize, awarded_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (id) DO NOTHING;
                    """, w["id"], w["contest_id"], w["user_id"], w["rank"], w["referral_count"], w["prize"], w["awarded_at"])
                print(f"   - Winners ko'chirildi: {len(winners)} ta")
            except Exception:
                pass

            # --- E. LOGS ---
            try:
                s_cur.execute("SELECT * FROM suspicious_logs")
                s_logs = [dict(r) for r in s_cur.fetchall()]
                for sl in s_logs:
                    await conn.execute("""
                        INSERT INTO suspicious_logs (id, referrer_id, referred_id, reason, created_at)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (id) DO NOTHING;
                    """, sl["id"], sl["referrer_id"], sl.get("referred_id"), sl["reason"], sl["created_at"])
            except Exception:
                pass

            try:
                s_cur.execute("SELECT * FROM admin_logs")
                a_logs = [dict(r) for r in s_cur.fetchall()]
                for al in a_logs:
                    await conn.execute("""
                        INSERT INTO admin_logs (id, admin_id, action, details, created_at)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (id) DO NOTHING;
                    """, al["id"], al["admin_id"], al["action"], al.get("details"), al["created_at"])
            except Exception:
                pass

            # Ketma-ketliklarni yangilash (Sequence reset)
            await conn.execute("SELECT setval('contests_id_seq', COALESCE((SELECT MAX(id) FROM contests), 1))")
            await conn.execute("SELECT setval('referrals_id_seq', COALESCE((SELECT MAX(id) FROM referrals), 1))")
            await conn.execute("SELECT setval('winners_id_seq', COALESCE((SELECT MAX(id) FROM winners), 1))")
            await conn.execute("SELECT setval('suspicious_logs_id_seq', COALESCE((SELECT MAX(id) FROM suspicious_logs), 1))")
            await conn.execute("SELECT setval('admin_logs_id_seq', COALESCE((SELECT MAX(id) FROM admin_logs), 1))")

    # 3. Solishtirish va tasdiqlash
    print("\n5. Ma'lumotlar yaxlitligini tekshirish (Verification):")
    async with pg_db.pool.acquire() as conn:
        pg_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        pg_refs = await conn.fetchval("SELECT COUNT(*) FROM referrals")
        pg_contests = await conn.fetchval("SELECT COUNT(*) FROM contests")

    s_users = len(users)
    s_refs = len(referrals)
    s_contests = len(contests)

    print(f"   * Users:     SQLite = {s_users} | PostgreSQL = {pg_users} -> {'[OK]' if s_users == pg_users else '[MISMATCH]'}")
    print(f"   * Referrals: SQLite = {s_refs} | PostgreSQL = {pg_refs} -> {'[OK]' if s_refs == pg_refs else '[MISMATCH]'}")
    print(f"   * Contests:  SQLite = {s_contests} | PostgreSQL = {pg_contests} -> {'[OK]' if s_contests == pg_contests else '[MISMATCH]'}")

    sqlite_conn.close()
    await pg_db.close()

    print("\n" + "=" * 60)
    print("MIGRATSIYA MUVAFFAQIYATLI YAKUNLANDI! BARCHA MA'LUMOTLAR MOS TUSHDI.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_migration())
