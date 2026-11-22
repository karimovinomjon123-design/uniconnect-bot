import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
import asyncpg
import config

logger = logging.getLogger(__name__)

def get_tashkent_now() -> datetime:
    """Toshkent vaqti bo'yicha (Asia/Tashkent, UTC+5) hozirgi vaqtni qaytaradi"""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Tashkent"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=5)))

def make_tashkent_aware(dt: datetime) -> datetime:
    """Sana vaqtini doimo Toshkent (UTC+5) vaqt mintaqasiga o'tkazish"""
    tashkent_tz = timezone(timedelta(hours=5))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tashkent_tz)
    return dt.astimezone(tashkent_tz)

class PostgresDatabase:
    """
    Neon Serverless PostgreSQL Database Engine.
    asyncpg connection pool asosida ishlaydi.
    Neon'ning Free Tier resurs chegaralariga (max 10 pool, SSL, auto-reconnect) to'liq moslangan.
    """
    def __init__(self, database_url: str):
        from urllib.parse import urlparse, urlencode, urlunparse, parse_qs
        raw = database_url
        if raw.startswith("postgres://"):
            raw = "postgresql://" + raw[len("postgres://"):]
        # Remove asyncpg-unsupported query parameters (channel_binding)
        p = urlparse(raw)
        qs = {k: v[0] for k, v in parse_qs(p.query).items() if k not in ("channel_binding",)}
        clean = urlunparse((p.scheme, p.netloc, p.path, "", urlencode(qs), ""))
        self.dsn = clean
        self.pool: Optional[asyncpg.Pool] = None

    async def init_db(self):
        """PostgreSQL jadvallari, ketma-ketliklari va indekslarini yaratish"""
        if not self.pool:
            is_neon = "neon.tech" in self.dsn
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                direct_tls=is_neon,
                min_size=2,
                max_size=10,
                max_inactive_connection_lifetime=300.0,
                command_timeout=60.0
            )

        async with self.pool.acquire() as conn:
            # 1. Users jadvali (Telegram ID lar BIGINT bo'lishi shart!)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    referrer_id BIGINT,
                    is_verified INTEGER DEFAULT 0,
                    referral_count INTEGER DEFAULT 0,
                    contest_referrals INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TEXT NOT NULL
                )
            """)

            # 2. Contests jadvali
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS contests (
                    id SERIAL PRIMARY KEY,
                    season INTEGER NOT NULL DEFAULT 1,
                    title TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    prize_1 TEXT NOT NULL,
                    prize_2 TEXT NOT NULL,
                    prize_3 TEXT NOT NULL,
                    min_referrals INTEGER DEFAULT 20,
                    status VARCHAR(20) DEFAULT 'upcoming',
                    created_at TEXT NOT NULL
                )
            """)

            # 3. Referrals jadvali
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id BIGSERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    referred_id BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                    status VARCHAR(20) DEFAULT 'pending',
                    contest_id INTEGER REFERENCES contests(id) ON DELETE SET NULL,
                    is_contest_credit INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    confirmed_at TEXT
                )
            """)

            # 4. Winners jadvali
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS winners (
                    id SERIAL PRIMARY KEY,
                    contest_id INTEGER NOT NULL REFERENCES contests(id) ON DELETE CASCADE,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    rank INTEGER NOT NULL,
                    referral_count INTEGER NOT NULL,
                    prize TEXT NOT NULL,
                    awarded_at TEXT NOT NULL
                )
            """)

            # 5. Suspicious logs jadvali
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS suspicious_logs (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL,
                    referred_id BIGINT,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # 6. Admin logs jadvali
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Indekslar
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_users_contest ON users(contest_referrals DESC)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_users_alltime ON users(referral_count DESC)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_referrals_referrer ON referrals(referrer_id, status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_referrals_dates ON referrals(created_at)")

            # Dastlabki 7 kunlik tanlov mavjudligini tekshirish
            c_row = await conn.fetchrow("SELECT id FROM contests WHERE id = 1")
            if not c_row:
                now_str = get_tashkent_now().isoformat()
                await conn.execute("""
                    INSERT INTO contests (id, season, title, start_date, end_date, prize_1, prize_2, prize_3, min_referrals, status, created_at)
                    VALUES (1, 1, $1, $2, $3, $4, $5, $6, $7, 'upcoming', $8)
                    ON CONFLICT (id) DO NOTHING
                """,
                    config.COMPETITION_NAME,
                    config.COMPETITION_START_ISO,
                    config.COMPETITION_END_ISO,
                    config.PRIZE_1,
                    config.PRIZE_2,
                    config.PRIZE_3,
                    config.MIN_REFERRALS_FOR_PRIZE,
                    now_str
                )
                await conn.execute("SELECT setval('contests_id_seq', COALESCE((SELECT MAX(id) FROM contests), 1))")

    async def close(self):
        """Connection poolni xavfsiz yopish"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    # ================= FOYDALANUVCHILAR BOSHQARUVI =================

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None

    async def add_user(self, user_id: int, username: Optional[str], full_name: str, referrer_id: Optional[int] = None) -> bool:
        """
        Yangi foydalanuvchini ro'yxatga olish.
        Anti-cheat qoidalari:
        - Takroriy ro'yxatdan o'tish yangi referral yaratmaydi.
        - O'zini o'zi taklif qilish (self-referral) bloklanadi.
        - Bir foydalanuvchi faqat bitta taklifchiga biriktirilishi mumkin.
        """
        if referrer_id is not None and int(referrer_id) == int(user_id):
            referrer_id = None

        now = get_tashkent_now().isoformat()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                existing = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1", user_id)
                if existing:
                    await conn.execute("""
                        UPDATE users SET username = $1, full_name = $2 WHERE user_id = $3
                    """, username, full_name, user_id)
                    return False

                # Yangi foydalanuvchi
                await conn.execute("""
                    INSERT INTO users (user_id, username, full_name, referrer_id, is_verified, referral_count, contest_referrals, status, created_at)
                    VALUES ($1, $2, $3, $4, 0, 0, 0, 'active', $5)
                """, user_id, username, full_name, referrer_id, now)

                # Referrals jadvaliga pending sifatida kiritish
                if referrer_id and referrer_id != user_id:
                    ref_user = await conn.fetchrow("SELECT user_id, status FROM users WHERE user_id = $1", referrer_id)
                    if ref_user and ref_user["status"] == 'active':
                        c_row = await conn.fetchrow("SELECT id FROM contests WHERE status IN ('upcoming', 'running') ORDER BY id DESC LIMIT 1")
                        contest_id = c_row["id"] if c_row else None

                        await conn.execute("""
                            INSERT INTO referrals (referrer_id, referred_id, status, contest_id, is_contest_credit, created_at)
                            VALUES ($1, $2, 'pending', $3, 0, $4)
                            ON CONFLICT (referred_id) DO NOTHING
                        """, referrer_id, user_id, contest_id, now)

                return True

    # ================= REFERRAL VA KANAL TEKSHIRUVI =================

    async def verify_user_and_confirm_referral(self, user_id: int) -> Tuple[bool, Optional[int], int, bool]:
        """
        Foydalanuvchi kanal va guruhga a'zo bo'lganida referralni tasdiqlash.
        Qaytaradi: (yangi_tasdiqlandimi, taklifchi_id, taklifchining_yangi_tanlov_balli, tanlovga_hisoblandimi)
        """
        now_dt = get_tashkent_now()
        now_str = now_dt.isoformat()

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                user = await conn.fetchrow("SELECT is_verified, referrer_id FROM users WHERE user_id = $1", user_id)
                if not user:
                    return False, None, 0, False

                was_verified = bool(user["is_verified"])
                referrer_id = user["referrer_id"]

                if not was_verified:
                    await conn.execute("UPDATE users SET is_verified = 1 WHERE user_id = $1", user_id)

                referrer_new_count = 0
                counted_referrer_id = None
                credited_to_contest = False

                if referrer_id and referrer_id != user_id:
                    ref_row = await conn.fetchrow("""
                        SELECT id, status, contest_id, is_contest_credit FROM referrals
                        WHERE referred_id = $1 AND referrer_id = $2
                    """, user_id, referrer_id)

                    if ref_row and ref_row["status"] in ('pending', 'unsubscribed'):
                        ref_id_pk = ref_row["id"]
                        contest_id = ref_row["contest_id"]

                        # Tanlov holatini tekshirish
                        contest = await conn.fetchrow("SELECT id, start_date, end_date, status FROM contests WHERE id = $1", contest_id)
                        is_during_contest = False
                        if contest:
                            s_dt = make_tashkent_aware(datetime.fromisoformat(contest["start_date"]))
                            e_dt = make_tashkent_aware(datetime.fromisoformat(contest["end_date"]))
                            c_status = contest["status"]
                            if c_status == 'running' and (s_dt <= now_dt <= e_dt):
                                is_during_contest = True

                        if is_during_contest:
                            credited_to_contest = True
                            await conn.execute("""
                                UPDATE referrals
                                SET status = 'confirmed', confirmed_at = $1, is_contest_credit = 1
                                WHERE id = $2
                            """, now_str, ref_id_pk)

                            await conn.execute("""
                                UPDATE users
                                SET referral_count = referral_count + 1,
                                    contest_referrals = contest_referrals + 1
                                WHERE user_id = $1
                            """, referrer_id)
                        else:
                            await conn.execute("""
                                UPDATE referrals
                                SET status = 'confirmed', confirmed_at = $1, is_contest_credit = 0
                                WHERE id = $2
                            """, now_str, ref_id_pk)

                            await conn.execute("""
                                UPDATE users
                                SET referral_count = referral_count + 1
                                WHERE user_id = $1
                            """, referrer_id)

                        # Shubhali faollikni tekshirish (oxirgi 2 daqiqada 5 tadan ortiq taklif)
                        recent_count = await conn.fetchval("""
                            SELECT COUNT(*) FROM referrals
                            WHERE referrer_id = $1 AND status = 'confirmed' AND confirmed_at >= $2
                        """, referrer_id, (now_dt - timedelta(minutes=2)).isoformat())

                        if recent_count and recent_count >= 5:
                            await conn.execute("""
                                INSERT INTO suspicious_logs (referrer_id, referred_id, reason, created_at)
                                VALUES ($1, $2, $3, $4)
                            """, referrer_id, user_id, f"Tezkor ketma-ketlik: 2 daqiqada {recent_count} ta taklif", now_str)

                        referrer_new_count = await conn.fetchval("SELECT contest_referrals FROM users WHERE user_id = $1", referrer_id) or 0
                        counted_referrer_id = referrer_id

                return (not was_verified), counted_referrer_id, referrer_new_count, credited_to_contest

    async def handle_user_unsubscribed(self, user_id: int) -> Tuple[bool, Optional[int], int]:
        """
        Foydalanuvchi kanal yoki guruhdan chiqib ketganda jarima qo'llash (-1 ball).
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                user = await conn.fetchrow("SELECT is_verified, referrer_id FROM users WHERE user_id = $1", user_id)
                if not user:
                    return False, None, 0

                was_verified = bool(user["is_verified"])
                referrer_id = user["referrer_id"]

                if was_verified:
                    await conn.execute("UPDATE users SET is_verified = 0 WHERE user_id = $1", user_id)

                deducted_referrer_id = None
                referrer_new_count = 0

                if referrer_id and referrer_id != user_id:
                    ref_row = await conn.fetchrow("""
                        SELECT id, status, is_contest_credit FROM referrals
                        WHERE referred_id = $1 AND referrer_id = $2
                    """, user_id, referrer_id)

                    if ref_row and ref_row["status"] == 'confirmed':
                        ref_id_pk = ref_row["id"]
                        was_contest_credit = bool(ref_row["is_contest_credit"])

                        await conn.execute("UPDATE referrals SET status = 'unsubscribed' WHERE id = $1", ref_id_pk)

                        if was_contest_credit:
                            await conn.execute("""
                                UPDATE users
                                SET referral_count = GREATEST(0, referral_count - 1),
                                    contest_referrals = GREATEST(0, contest_referrals - 1)
                                WHERE user_id = $1
                            """, referrer_id)
                        else:
                            await conn.execute("""
                                UPDATE users
                                SET referral_count = GREATEST(0, referral_count - 1)
                                WHERE user_id = $1
                            """, referrer_id)

                        referrer_new_count = await conn.fetchval("SELECT contest_referrals FROM users WHERE user_id = $1", referrer_id) or 0
                        deducted_referrer_id = referrer_id

                return was_verified, deducted_referrer_id, referrer_new_count

    # ================= TANLOV VA AVTOMATIK BOSHQARUV =================

    async def get_active_contest(self) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM contests ORDER BY id DESC LIMIT 1")
            if not row:
                return None

            data = dict(row)
            start_dt = make_tashkent_aware(datetime.fromisoformat(data["start_date"]))
            end_dt = make_tashkent_aware(datetime.fromisoformat(data["end_date"]))
            now_dt = get_tashkent_now()

            if data["status"] != "ended":
                if now_dt < start_dt:
                    calculated_status = "upcoming"
                    rem = start_dt - now_dt
                    days = rem.days
                    hours, rem_s = divmod(rem.seconds, 3600)
                    minutes, _ = divmod(rem_s, 60)
                    data["time_left_str"] = f"{days} kun, {hours} soat, {minutes} daqiqa (Boshlanishiga)"
                    data["state_badge"] = "⏳ Kutilmoqda (Tez kunda)"
                elif start_dt <= now_dt <= end_dt:
                    calculated_status = "running"
                    rem = end_dt - now_dt
                    days = rem.days
                    hours, rem_s = divmod(rem.seconds, 3600)
                    minutes, _ = divmod(rem_s, 60)
                    data["time_left_str"] = f"{days} kun, {hours} soat, {minutes} daqiqa (Tugashiga)"
                    data["state_badge"] = "🚀 Faol davom etmoqda"
                else:
                    calculated_status = "ended"
                    data["time_left_str"] = "🏁 Tanlov yakunlandi"
                    data["state_badge"] = "🏁 Yakunlangan"

                if calculated_status != data["status"]:
                    await conn.execute("UPDATE contests SET status = $1 WHERE id = $2", calculated_status, data["id"])
                    data["status"] = calculated_status
            else:
                data["time_left_str"] = "🏁 Tanlov yakunlandi"
                data["state_badge"] = "🏁 Yakunlangan"

            return data

    async def sync_contest_status(self) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        contest = await self.get_active_contest()
        if not contest:
            return None, None

        cid = contest["id"]
        status = contest["status"]

        if status == "ended":
            async with self.pool.acquire() as conn:
                w_count = await conn.fetchval("SELECT COUNT(*) FROM winners WHERE contest_id = $1", cid)
                if w_count == 0:
                    await self.finalize_contest_and_record_winners(cid)
                    return "finalized", contest

        return None, contest

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def get_active_participants_count(self) -> int:
        """Reyting sahifalash uchun tasdiqlangan faol foydalanuvchilar soni"""
        async with self.pool.acquire() as conn:
            val = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_verified = 1 AND status = 'active'")
            return val or 0

    async def set_contest_status(self, contest_id: int, status: str):
        """Tanlov holatini o'zgartirish (masalan: 'running' yoki 'ended')"""
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE contests SET status = $1 WHERE id = $2", status, contest_id)

    async def get_leaderboard(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Reyting ro'yxati (kamida 20 ta taklif talabi bo'yicha da'vogarlik ko'rsatiladi)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, username, full_name, contest_referrals, referral_count
                FROM users
                WHERE is_verified = 1 AND status = 'active'
                ORDER BY contest_referrals DESC, created_at ASC
                LIMIT $1 OFFSET $2
            """, limit, offset)

            res = []
            for r in rows:
                item = dict(r)
                pts = item["contest_referrals"]
                item["is_eligible"] = (pts >= config.MIN_REFERRALS_FOR_PRIZE)
                item["needed_to_min"] = max(0, config.MIN_REFERRALS_FOR_PRIZE - pts)
                res.append(item)
            return res

    async def get_user_contest_standing(self, user_id: int) -> Dict[str, Any]:
        """Foydalanuvchining shaxsiy tanlov ko'rsatkichlari"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT contest_referrals, referral_count, is_verified FROM users WHERE user_id = $1", user_id)
            if not row:
                return {
                    "rank": 0,
                    "contest_referrals": 0,
                    "alltime_referrals": 0,
                    "is_eligible": False,
                    "needed_to_min": config.MIN_REFERRALS_FOR_PRIZE,
                    "diff_to_top3": config.MIN_REFERRALS_FOR_PRIZE
                }

            user_pts = row["contest_referrals"]
            alltime = row["referral_count"]

            rank_val = await conn.fetchval("""
                SELECT COUNT(*) FROM users
                WHERE contest_referrals > $1 AND is_verified = 1 AND status = 'active'
            """, user_pts)
            rank = (rank_val or 0) + 1

            is_eligible = (user_pts >= config.MIN_REFERRALS_FOR_PRIZE)
            needed_to_min = max(0, config.MIN_REFERRALS_FOR_PRIZE - user_pts)

            third_score = await conn.fetchval("""
                SELECT contest_referrals FROM users
                WHERE is_verified = 1 AND status = 'active'
                ORDER BY contest_referrals DESC, created_at ASC
                LIMIT 1 OFFSET 2
            """)

            if third_score is not None:
                target_score = max(third_score + 1, config.MIN_REFERRALS_FOR_PRIZE)
                diff_to_top3 = max(0, target_score - user_pts)
            else:
                diff_to_top3 = needed_to_min

            return {
                "rank": rank,
                "contest_referrals": user_pts,
                "alltime_referrals": alltime,
                "is_eligible": is_eligible,
                "needed_to_min": needed_to_min,
                "diff_to_top3": diff_to_top3
            }

    async def finalize_contest_and_record_winners(self, contest_id: int) -> List[Dict[str, Any]]:
        """Tanlovni yakunlash va QAT'IY 20+ TAKLIF talabi bo'yicha g'oliblarni aniqlash"""
        now = get_tashkent_now().isoformat()
        prizes = [config.PRIZE_1, config.PRIZE_2, config.PRIZE_3]

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE contests SET status = 'ended' WHERE id = $1", contest_id)

                # Qat'iy kamida 20 ta taklif to'plaganlar orasidan Top 3 olinadi
                rows = await conn.fetch("""
                    SELECT user_id, username, full_name, contest_referrals
                    FROM users
                    WHERE contest_referrals >= $1 AND is_verified = 1 AND status = 'active'
                    ORDER BY contest_referrals DESC, created_at ASC
                    LIMIT 3
                """, config.MIN_REFERRALS_FOR_PRIZE)
                candidates = [dict(r) for r in rows]

                await conn.execute("DELETE FROM winners WHERE contest_id = $1", contest_id)

                winners = []
                for idx, c in enumerate(candidates):
                    rank = idx + 1
                    prize_name = prizes[idx]
                    await conn.execute("""
                        INSERT INTO winners (contest_id, user_id, rank, referral_count, prize, awarded_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, contest_id, c["user_id"], rank, c["contest_referrals"], prize_name, now)

                    c["rank"] = rank
                    c["prize"] = prize_name
                    winners.append(c)

                return winners

    async def get_winners(self, contest_id: Optional[int] = None) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            if contest_id:
                rows = await conn.fetch("""
                    SELECT w.*, u.username, u.full_name
                    FROM winners w
                    JOIN users u ON w.user_id = u.user_id
                    WHERE w.contest_id = $1
                    ORDER BY w.rank ASC
                """, contest_id)
            else:
                rows = await conn.fetch("""
                    SELECT w.*, u.username, u.full_name
                    FROM winners w
                    JOIN users u ON w.user_id = u.user_id
                    ORDER BY w.id DESC LIMIT 3
                """)
            return [dict(r) for r in rows]

    # ================= STATISTIKA VA ADMIN PANEL =================

    async def get_stats(self) -> Dict[str, Any]:
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users") or 0
            verified_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_verified = 1") or 0
            confirmed_refs = await conn.fetchval("SELECT COUNT(*) FROM referrals WHERE status = 'confirmed'") or 0

            today_str = get_tashkent_now().strftime("%Y-%m-%d")
            today_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE created_at LIKE $1", f"{today_str}%") or 0

            eligible_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE contest_referrals >= $1", config.MIN_REFERRALS_FOR_PRIZE) or 0

            return {
                "total_users": total_users,
                "verified_users": verified_users,
                "today_users": today_users,
                "total_referrals": confirmed_refs,
                "eligible_users": eligible_users
            }

    async def get_all_active_user_ids(self) -> List[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM users WHERE status = 'active'")
            return [r["user_id"] for r in rows]

    async def get_global_stats(self) -> Dict[str, Any]:
        return await self.get_stats()

    async def get_top_participants(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, username, full_name, contest_referrals, referral_count, created_at
                FROM users
                WHERE is_verified = 1 AND status = 'active'
                ORDER BY contest_referrals DESC, created_at ASC
                LIMIT $1
            """, limit)

            res = []
            for idx, r in enumerate(rows):
                item = dict(r)
                item["rank"] = idx + 1
                pts = item["contest_referrals"]
                item["is_eligible"] = (pts >= config.MIN_REFERRALS_FOR_PRIZE)
                item["needed_to_min"] = max(0, config.MIN_REFERRALS_FOR_PRIZE - pts)
                res.append(item)
            return res

    async def search_user(self, query: str | int) -> Optional[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            if str(query).isdigit():
                row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", int(query))
            else:
                clean_uname = str(query).replace("@", "").strip()
                row = await conn.fetchrow("SELECT * FROM users WHERE username ILIKE $1", clean_uname)
            return dict(row) if row else None

    async def get_user_referrals_list(self, user_id: int) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT r.referred_id, u.full_name, u.username, r.status, r.is_contest_credit, r.created_at, r.confirmed_at
                FROM referrals r
                LEFT JOIN users u ON r.referred_id = u.user_id
                WHERE r.referrer_id = $1
                ORDER BY r.id DESC
            """, user_id)
            return [dict(r) for r in rows]

    async def get_suspicious_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT s.*, u.full_name, u.username
                FROM suspicious_logs s
                LEFT JOIN users u ON s.referrer_id = u.user_id
                ORDER BY s.id DESC LIMIT $1
            """, limit)
            return [dict(r) for r in rows]

    async def export_participants_csv(self) -> str:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, username, full_name, referrer_id, is_verified,
                       contest_referrals, referral_count, status, created_at
                FROM users
                ORDER BY contest_referrals DESC, created_at ASC
            """)

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Telegram ID", "Username", "To'liq Ism", "Taklifchisi",
                "Kanal Tasdiqlangan", "Tanlov Balli (7 kun)", "Jami Takliflari",
                "Sovg'aga Da'vogar (>=20)", "Holati", "Ro'yxatdan O'tgan Vaqti"
            ])

            for r in rows:
                is_eligible = "HA (>=20)" if r["contest_referrals"] >= config.MIN_REFERRALS_FOR_PRIZE else "YO'Q"
                writer.writerow([
                    r["user_id"],
                    f"@{r['username']}" if r["username"] else "mavjud emas",
                    r["full_name"],
                    r["referrer_id"] or "To'g'ridan-to'g'ri",
                    "Ha" if r["is_verified"] else "Yo'q",
                    r["contest_referrals"],
                    r["referral_count"],
                    is_eligible,
                    r["status"],
                    r["created_at"]
                ])

            return output.getvalue()

    async def log_admin_action(self, admin_id: int, action: str, details: str = ""):
        now = get_tashkent_now().isoformat()
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO admin_logs (admin_id, action, details, created_at)
                VALUES ($1, $2, $3, $4)
            """, admin_id, action, details, now)

    async def get_admin_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM admin_logs ORDER BY id DESC LIMIT $1", limit)
            return [dict(r) for r in rows]

    async def start_new_season_contest(self, duration_days: int = 7) -> Dict[str, Any]:
        now = get_tashkent_now()
        end_time = now + timedelta(days=duration_days)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                last_season = await conn.fetchval("SELECT MAX(season) FROM contests") or 1
                new_season = last_season + 1

                await conn.execute("UPDATE contests SET status = 'ended' WHERE status IN ('upcoming', 'running')")
                await conn.execute("UPDATE users SET contest_referrals = 0")

                row = await conn.fetchrow("""
                    INSERT INTO contests (season, title, start_date, end_date, prize_1, prize_2, prize_3, min_referrals, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'running', $9)
                    RETURNING *
                """,
                    new_season,
                    f"UniConnect UZ — {new_season}-MAVSUM {duration_days} DAYS CHALLENGE",
                    now.isoformat(),
                    end_time.isoformat(),
                    config.PRIZE_1,
                    config.PRIZE_2,
                    config.PRIZE_3,
                    config.MIN_REFERRALS_FOR_PRIZE,
                    now.isoformat()
                )
                return dict(row) if row else {}
