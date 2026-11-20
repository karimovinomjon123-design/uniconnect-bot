import aiosqlite
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

class Database:
    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)

    async def init_db(self):
        """Ma'lumotlar bazasi jadvallarini yaratish va yangilash (migration)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    referrer_id INTEGER,
                    is_verified INTEGER DEFAULT 0,
                    referral_count INTEGER DEFAULT 0,
                    contest_referrals INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL
                )
            """)

            # Mavjud users jadvaliga contest_referrals ustunini xavfsiz qo'shish (agar bo'lmasa)
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in await cursor.fetchall()]
            if "contest_referrals" not in columns:
                await db.execute("ALTER TABLE users ADD COLUMN contest_referrals INTEGER DEFAULT 0")

            # Referrals jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL UNIQUE,
                    status TEXT DEFAULT 'pending',
                    contest_id INTEGER,
                    created_at TEXT NOT NULL,
                    confirmed_at TEXT,
                    FOREIGN KEY(referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY(referred_id) REFERENCES users(user_id)
                )
            """)

            cursor = await db.execute("PRAGMA table_info(referrals)")
            ref_columns = [row[1] for row in await cursor.fetchall()]
            if "contest_id" not in ref_columns:
                await db.execute("ALTER TABLE referrals ADD COLUMN contest_id INTEGER")

            # Contests (Mavsumiy tanlovlar va marafonlar) jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS contests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    season INTEGER NOT NULL DEFAULT 1,
                    title TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    prize_1 TEXT NOT NULL,
                    prize_2 TEXT NOT NULL,
                    prize_3 TEXT NOT NULL,
                    status TEXT DEFAULT 'running',
                    created_at TEXT NOT NULL
                )
            """)

            # Tezkor qidiruv indekslari
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_contest ON users(contest_referrals DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_alltime ON users(referral_count DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_referrals_status ON referrals(referrer_id, status)")

            # Agar faol tanlov bo'lmasa, dastlabki 7 kunlik tanlovni yaratamiz
            c_cur = await db.execute("SELECT COUNT(*) FROM contests WHERE status = 'running'")
            active_count = (await c_cur.fetchone())[0]
            if active_count == 0:
                now = datetime.now(timezone.utc)
                end_time = now + timedelta(days=7)
                await db.execute("""
                    INSERT INTO contests (season, title, start_date, end_date, prize_1, prize_2, prize_3, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)
                """, (
                    1,
                    "1-Mavsum: 7 Kunlik Talabalar Marafon-Konkursi 🚀",
                    now.isoformat(),
                    end_time.isoformat(),
                    "🥇 1-o'rin: Qimmatbaho Smartfon yoki Asosiy Pul Mukofoti",
                    "🥈 2-o'rin: Smart Soat (Smartwatch) yoki Sifatli Quloqchin",
                    "🥉 3-o'rin: UniConnect Brendli Maxsus Merch To'plami + Sertifikat",
                    now.isoformat()
                ))

            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def add_user(self, user_id: int, username: Optional[str], full_name: str, referrer_id: Optional[int] = None) -> bool:
        """Yangi foydalanuvchini ro'yxatga olish"""
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if await cursor.fetchone():
                await db.execute("""
                    UPDATE users SET username = ?, full_name = ? WHERE user_id = ?
                """, (username, full_name, user_id))
                await db.commit()
                return False

            # Yangi foydalanuvchini kiritish
            await db.execute("""
                INSERT INTO users (user_id, username, full_name, referrer_id, is_verified, referral_count, contest_referrals, status, created_at)
                VALUES (?, ?, ?, ?, 0, 0, 0, 'active', ?)
            """, (user_id, username, full_name, referrer_id, now))

            # Referrals jadvaliga pending sifatida yozish (o'zini o'zi taklif qilmagan bo'lsa)
            if referrer_id and referrer_id != user_id:
                ref_cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (referrer_id,))
                if await ref_cur.fetchone():
                    # Faol tanlov ID sini olamiz
                    cnt_cur = await db.execute("SELECT id FROM contests WHERE status = 'running' ORDER BY id DESC LIMIT 1")
                    cnt_row = await cnt_cur.fetchone()
                    contest_id = cnt_row[0] if cnt_row else None

                    await db.execute("""
                        INSERT OR IGNORE INTO referrals (referrer_id, referred_id, status, contest_id, created_at)
                        VALUES (?, ?, 'pending', ?, ?)
                    """, (referrer_id, user_id, contest_id, now))

            await db.commit()
            return True

    async def verify_user_and_confirm_referral(self, user_id: int) -> Tuple[bool, Optional[int], int]:
        """
        Kanal va guruh a'zoligini tasdiqlash.
        Agar referral 'pending' yoki 'unsubscribed' bo'lsa, uni 'confirmed' qiladi,
        taklifchining contest_referrals va referral_count'ini 1 taga oshiradi.
        """
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT is_verified, referrer_id FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            if not user:
                return False, None, 0

            was_verified = bool(user[0])
            referrer_id = user[1]

            if not was_verified:
                await db.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))

            referrer_new_count = 0
            counted_referrer_id = None

            if referrer_id and referrer_id != user_id:
                ref_cur = await db.execute("""
                    SELECT id, status FROM referrals WHERE referred_id = ? AND referrer_id = ?
                """, (user_id, referrer_id))
                ref_row = await ref_cur.fetchone()

                if ref_row and ref_row[1] in ('pending', 'unsubscribed'):
                    # Holatni tasdiqlash
                    await db.execute("""
                        UPDATE referrals SET status = 'confirmed', confirmed_at = ? WHERE id = ?
                    """, (now, ref_row[0]))

                    # Taklifchiga ball qo'shish (ham jami, ham joriy tanlov balli)
                    await db.execute("""
                        UPDATE users
                        SET referral_count = referral_count + 1,
                            contest_referrals = contest_referrals + 1
                        WHERE user_id = ?
                    """, (referrer_id,))

                    cnt_cur = await db.execute("SELECT contest_referrals FROM users WHERE user_id = ?", (referrer_id,))
                    cnt_row = await cnt_cur.fetchone()
                    referrer_new_count = cnt_row[0] if cnt_row else 0
                    counted_referrer_id = referrer_id

            await db.commit()
            return (not was_verified), counted_referrer_id, referrer_new_count

    async def handle_user_unsubscribed(self, user_id: int) -> Tuple[bool, Optional[int], int]:
        """
        Foydalanuvchi kanal yoki guruhdan chiqib ketganda ishlaydi.
        Kanal a'zoligini bekor qiladi va agar u orqali taklifchiga ball berilgan bo'lsa,
        taklifchidan 1 ballni ayirib tashlaydi (soxta obunalardan himoya).
        Qaytaradi: (bekor qilindimi, taklifchi_id, taklifchining yangi balli)
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT is_verified, referrer_id FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            if not user:
                return False, None, 0

            was_verified = bool(user[0])
            referrer_id = user[1]

            if was_verified:
                await db.execute("UPDATE users SET is_verified = 0 WHERE user_id = ?", (user_id,))

            deducted_referrer_id = None
            referrer_new_count = 0

            if referrer_id and referrer_id != user_id:
                ref_cur = await db.execute("""
                    SELECT id, status FROM referrals WHERE referred_id = ? AND referrer_id = ?
                """, (user_id, referrer_id))
                ref_row = await ref_cur.fetchone()

                if ref_row and ref_row[1] == 'confirmed':
                    await db.execute("""
                        UPDATE referrals SET status = 'unsubscribed' WHERE id = ?
                    """, (ref_row[0],))

                    # Ballni ayirish (manfiy songa tushib ketmasligi uchun MAX(0, ...))
                    await db.execute("""
                        UPDATE users
                        SET referral_count = MAX(0, referral_count - 1),
                            contest_referrals = MAX(0, contest_referrals - 1)
                        WHERE user_id = ?
                    """, (referrer_id,))

                    cnt_cur = await db.execute("SELECT contest_referrals FROM users WHERE user_id = ?", (referrer_id,))
                    cnt_row = await cnt_cur.fetchone()
                    referrer_new_count = cnt_row[0] if cnt_row else 0
                    deducted_referrer_id = referrer_id

            await db.commit()
            return was_verified, deducted_referrer_id, referrer_new_count

    # ================= TANLOV VA REYTING (CONTEST & LEADERBOARD) =================

    async def get_active_contest(self) -> Optional[Dict[str, Any]]:
        """Joriy faol tanlov ma'lumotlari va qolgan vaqt"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM contests WHERE status = 'running' ORDER BY id DESC LIMIT 1
            """)
            row = await cursor.fetchone()
            if not row:
                return None

            data = dict(row)
            end_dt = datetime.fromisoformat(data["end_date"])
            now_dt = datetime.now(timezone.utc)
            remaining = end_dt - now_dt

            if remaining.total_seconds() <= 0:
                data["is_ended"] = True
                data["time_left_str"] = "🏁 Tanlov yakunlandi! G'oliblar e'lon qilinmoqda..."
            else:
                days = remaining.days
                hours, rem = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(rem, 60)
                data["is_ended"] = False
                data["time_left_str"] = f"{days} kun, {hours} soat, {minutes} daqiqa"

            return data

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Joriy tanlov bo'yicha eng ko'p ball to'plagan yetakchilar (Top 10)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT user_id, username, full_name, contest_referrals, referral_count
                FROM users
                WHERE is_verified = 1 AND status = 'active'
                ORDER BY contest_referrals DESC, created_at ASC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_user_contest_rank(self, user_id: int) -> Tuple[int, int, int]:
        """
        Foydalanuvchining joriy tanlovdagi o'rni, balli va Top 3 ga kirishi uchun qolgan ball.
        Qaytaradi: (rank, user_points, diff_to_top3)
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT contest_referrals, is_verified FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                return 0, 0, 0

            user_points = row[0]

            # Foydalanuvchining o'rni
            rank_cur = await db.execute("""
                SELECT COUNT(*) FROM users
                WHERE contest_referrals > ? AND is_verified = 1 AND status = 'active'
            """, (user_points,))
            rank = (await rank_cur.fetchone())[0] + 1

            # Top 3 ga kirish uchun qancha ball kerakligini hisoblash
            # 3-o'rindagi foydalanuvchining ballini olamiz
            top3_cur = await db.execute("""
                SELECT contest_referrals FROM users
                WHERE is_verified = 1 AND status = 'active'
                ORDER BY contest_referrals DESC, created_at ASC
                LIMIT 1 OFFSET 2
            """)
            top3_row = await top3_cur.fetchone()
            if top3_row:
                third_points = top3_row[0]
                diff_to_top3 = max(0, third_points - user_points + 1)
            else:
                diff_to_top3 = 1  # Agar 3 ta ishtirokchi ham bo'lmasa, 1 ta taklif bilan kiradi

            return rank, user_points, diff_to_top3

    async def end_contest_and_get_winners(self, contest_id: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Tanlovni yakunlash va Top 3 g'oliblarni aniqlash"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("UPDATE contests SET status = 'ended' WHERE id = ?", (contest_id,))
            await db.commit()

            c_cur = await db.execute("SELECT * FROM contests WHERE id = ?", (contest_id,))
            contest = dict(await c_cur.fetchone())

            winners = await self.get_leaderboard(limit=3)
            return contest, winners

    async def start_new_contest(self, duration_days: int = 7) -> Dict[str, Any]:
        """Yangi tanlov mavsumini boshlash va ballarni 0 dan yangilash"""
        now = datetime.now(timezone.utc)
        end_time = now + timedelta(days=duration_days)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Oxirgi mavsum raqamini aniqlash
            last_cur = await db.execute("SELECT MAX(season) FROM contests")
            last_season = (await last_cur.fetchone())[0] or 0
            new_season = last_season + 1

            # Eskilarini yakunlash
            await db.execute("UPDATE contests SET status = 'ended' WHERE status = 'running'")

            # Foydalanuvchilarning tanlov ballarini yangilash (umumiy ballari saqlanadi)
            await db.execute("UPDATE users SET contest_referrals = 0")

            await db.execute("""
                INSERT INTO contests (season, title, start_date, end_date, prize_1, prize_2, prize_3, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)
            """, (
                new_season,
                f"{new_season}-Mavsum: {duration_days} Kunlik Talabalar Marafon-Konkursi 🚀",
                now.isoformat(),
                end_time.isoformat(),
                "🥇 1-o'rin: Qimmatbaho Smartfon yoki Asosiy Pul Mukofoti",
                "🥈 2-o'rin: Smart Soat (Smartwatch) yoki Sifatli Quloqchin",
                "🥉 3-o'rin: UniConnect Brendli Maxsus Merch To'plami + Sertifikat",
                now.isoformat()
            ))
            await db.commit()

            cur = await db.execute("SELECT * FROM contests WHERE status = 'running' ORDER BY id DESC LIMIT 1")
            return dict(await cur.fetchone())

    # ================= ADMIN STATISTIKA VA XIZMATLAR =================

    async def get_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            total_users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            verified_users = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")).fetchone())[0]
            confirmed_refs = (await (await db.execute("SELECT COUNT(*) FROM referrals WHERE status = 'confirmed'")).fetchone())[0]

            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            today_users = (await (await db.execute("SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (f"{today_str}%",))).fetchone())[0]

            return {
                "total_users": total_users,
                "verified_users": verified_users,
                "today_users": today_users,
                "total_referrals": confirmed_refs,
            }

    async def get_all_active_user_ids(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE status = 'active'")
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def search_user(self, query: str | int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if str(query).isdigit():
                cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (int(query),))
            else:
                clean_uname = str(query).replace("@", "").strip()
                cursor = await db.execute("SELECT * FROM users WHERE username LIKE ?", (clean_uname,))
            row = await cursor.fetchone()
            return dict(row) if row else None
