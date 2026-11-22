import aiosqlite
import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
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

class Database:
    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)

    async def init_db(self):
        """Ma'lumotlar bazasi jadvallarini yaratish va xavfsiz yangilash"""
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Users jadvali
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

            # Mavjud ustunlarni tekshirish (migration)
            cursor = await db.execute("PRAGMA table_info(users)")
            user_cols = [row[1] for row in await cursor.fetchall()]
            if "contest_referrals" not in user_cols:
                await db.execute("ALTER TABLE users ADD COLUMN contest_referrals INTEGER DEFAULT 0")

            # 2. Referrals jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL UNIQUE,
                    status TEXT DEFAULT 'pending',
                    contest_id INTEGER,
                    is_contest_credit INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    confirmed_at TEXT,
                    FOREIGN KEY(referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY(referred_id) REFERENCES users(user_id)
                )
            """)

            cursor = await db.execute("PRAGMA table_info(referrals)")
            ref_cols = [row[1] for row in await cursor.fetchall()]
            if "contest_id" not in ref_cols:
                await db.execute("ALTER TABLE referrals ADD COLUMN contest_id INTEGER")
            if "is_contest_credit" not in ref_cols:
                await db.execute("ALTER TABLE referrals ADD COLUMN is_contest_credit INTEGER DEFAULT 0")

            # 3. Contests (Tanlovlar) jadvali
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
                    min_referrals INTEGER NOT NULL DEFAULT 20,
                    status TEXT DEFAULT 'upcoming',
                    created_at TEXT NOT NULL
                )
            """)

            cursor = await db.execute("PRAGMA table_info(contests)")
            contest_cols = [row[1] for row in await cursor.fetchall()]
            if "min_referrals" not in contest_cols:
                await db.execute("ALTER TABLE contests ADD COLUMN min_referrals INTEGER DEFAULT 20")

            # 4. Winners (G'oliblar) jadvali
            await db.execute("""
                CREATE TABLE IF NOT EXISTS winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contest_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    rank INTEGER NOT NULL,
                    referral_count INTEGER NOT NULL,
                    prize TEXT NOT NULL,
                    awarded_at TEXT NOT NULL,
                    FOREIGN KEY(contest_id) REFERENCES contests(id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)

            # 5. Suspicious logs (Shubhali takliflar logi)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS suspicious_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # 6. Admin logs (Admin harakatlari jurnali)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Indekslar
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_contest ON users(contest_referrals DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_users_alltime ON users(referral_count DESC)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id, status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_referrals_dates ON referrals(created_at)")

            # Tanlovni sozlash (agar mavjud bo'lmasa yoki yangi talablarga moslashtirish)
            now_tashkent = get_tashkent_now()
            cursor = await db.execute("SELECT id FROM contests WHERE title = ? OR status IN ('upcoming', 'running')", (config.COMPETITION_NAME,))
            existing = await cursor.fetchone()

            if not existing:
                # Yangi tanlovni kiritish
                await db.execute("""
                    INSERT INTO contests (season, title, start_date, end_date, prize_1, prize_2, prize_3, min_referrals, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    1,
                    config.COMPETITION_NAME,
                    config.COMPETITION_START_ISO,
                    config.COMPETITION_END_ISO,
                    config.PRIZE_1,
                    config.PRIZE_2,
                    config.PRIZE_3,
                    config.MIN_REFERRALS_FOR_PRIZE,
                    "upcoming" if now_tashkent < datetime.fromisoformat(config.COMPETITION_START_ISO) else "running",
                    now_tashkent.isoformat()
                ))
            else:
                # Mavjud tanlov ma'lumotlarini rasmiy talablarga yangilaymiz
                await db.execute("""
                    UPDATE contests
                    SET title = ?,
                        start_date = ?,
                        end_date = ?,
                        prize_1 = ?,
                        prize_2 = ?,
                        prize_3 = ?,
                        min_referrals = ?
                    WHERE id = ?
                """, (
                    config.COMPETITION_NAME,
                    config.COMPETITION_START_ISO,
                    config.COMPETITION_END_ISO,
                    config.PRIZE_1,
                    config.PRIZE_2,
                    config.PRIZE_3,
                    config.MIN_REFERRALS_FOR_PRIZE,
                    existing[0]
                ))

            await db.commit()

    # ================= FOYDALANUVCHILAR BOSHQARUVI =================

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
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
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if await cursor.fetchone():
                # Mavjud foydalanuvchi ma'lumotlarini yangilash (referral o'zgarmaydi)
                await db.execute("""
                    UPDATE users SET username = ?, full_name = ? WHERE user_id = ?
                """, (username, full_name, user_id))
                await db.commit()
                return False

            # Yangi foydalanuvchi
            await db.execute("""
                INSERT INTO users (user_id, username, full_name, referrer_id, is_verified, referral_count, contest_referrals, status, created_at)
                VALUES (?, ?, ?, ?, 0, 0, 0, 'active', ?)
            """, (user_id, username, full_name, referrer_id, now))

            # Referrals jadvaliga pending sifatida kiritish
            if referrer_id and referrer_id != user_id:
                ref_cur = await db.execute("SELECT user_id, status FROM users WHERE user_id = ?", (referrer_id,))
                ref_user = await ref_cur.fetchone()
                if ref_user and ref_user[1] == 'active':
                    # Joriy tanlov ID sini olamiz
                    c_cur = await db.execute("SELECT id FROM contests WHERE status IN ('upcoming', 'running') ORDER BY id DESC LIMIT 1")
                    c_row = await c_cur.fetchone()
                    contest_id = c_row[0] if c_row else None

                    await db.execute("""
                        INSERT OR IGNORE INTO referrals (referrer_id, referred_id, status, contest_id, is_contest_credit, created_at)
                        VALUES (?, ?, 'pending', ?, 0, ?)
                    """, (referrer_id, user_id, contest_id, now))

            await db.commit()
            return True

    # ================= REFERRAL VA KANAL TEKSHIRUVI =================

    async def verify_user_and_confirm_referral(self, user_id: int) -> Tuple[bool, Optional[int], int, bool]:
        """
        Foydalanuvchi kanal va guruhga a'zo bo'lganida referralni tasdiqlash.
        Qoidalar:
        - Agar tanlov faol (running) bo'lsa, tanlov balli (contest_referrals) qo'shiladi.
        - Agar tanlov hali boshlanmagan bo'lsa (upcoming) yoki tugagan bo'lsa (ended), tanlov balli berilmaydi.
        Qaytaradi: (yangi_tasdiqlandimi, taklifchi_id, taklifchining_yangi_tanlov_balli, tanlovga_hisoblandimi)
        """
        now_dt = get_tashkent_now()
        now_str = now_dt.isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT is_verified, referrer_id FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            if not user:
                return False, None, 0, False

            was_verified = bool(user[0])
            referrer_id = user[1]

            if not was_verified:
                await db.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))

            referrer_new_count = 0
            counted_referrer_id = None
            credited_to_contest = False

            if referrer_id and referrer_id != user_id:
                ref_cur = await db.execute("""
                    SELECT id, status, contest_id, is_contest_credit FROM referrals
                    WHERE referred_id = ? AND referrer_id = ?
                """, (user_id, referrer_id))
                ref_row = await ref_cur.fetchone()

                if ref_row and ref_row[1] in ('pending', 'unsubscribed'):
                    ref_id_pk = ref_row[0]
                    contest_id = ref_row[2]

                    # Tanlov holatini tekshiramiz
                    c_cur = await db.execute("SELECT id, start_date, end_date, status FROM contests WHERE id = ?", (contest_id,))
                    contest = await c_cur.fetchone()

                    is_during_contest = False
                    if contest:
                        s_dt = make_tashkent_aware(datetime.fromisoformat(contest[1]))
                        e_dt = make_tashkent_aware(datetime.fromisoformat(contest[2]))
                        c_status = contest[3]
                        if c_status == 'running' and (s_dt <= now_dt <= e_dt):
                            is_during_contest = True

                    # Ball hisoblash
                    if is_during_contest:
                        credited_to_contest = True
                        await db.execute("""
                            UPDATE referrals
                            SET status = 'confirmed', confirmed_at = ?, is_contest_credit = 1
                            WHERE id = ?
                        """, (now_str, ref_id_pk))

                        await db.execute("""
                            UPDATE users
                            SET referral_count = referral_count + 1,
                                contest_referrals = contest_referrals + 1
                            WHERE user_id = ?
                        """, (referrer_id,))
                    else:
                        # Tanlov vaqtidan tashqari: faqat umumiy takliflar soniga qo'shiladi
                        await db.execute("""
                            UPDATE referrals
                            SET status = 'confirmed', confirmed_at = ?, is_contest_credit = 0
                            WHERE id = ?
                        """, (now_str, ref_id_pk))

                        await db.execute("""
                            UPDATE users
                            SET referral_count = referral_count + 1
                            WHERE user_id = ?
                        """, (referrer_id,))

                    # Shubhali faollikni tekshirish (oxirgi 2 daqiqada 5 tadan ortiq taklif)
                    recent_cur = await db.execute("""
                        SELECT COUNT(*) FROM referrals
                        WHERE referrer_id = ? AND status = 'confirmed' AND confirmed_at >= ?
                    """, (referrer_id, (now_dt - timedelta(minutes=2)).isoformat()))
                    recent_count = (await recent_cur.fetchone())[0]
                    if recent_count >= 5:
                        await db.execute("""
                            INSERT INTO suspicious_logs (referrer_id, referred_id, reason, created_at)
                            VALUES (?, ?, ?, ?)
                        """, (referrer_id, user_id, f"Tezkor ketma-ketlik: 2 daqiqada {recent_count} ta taklif", now_str))

                    cnt_cur = await db.execute("SELECT contest_referrals FROM users WHERE user_id = ?", (referrer_id,))
                    cnt_row = await cnt_cur.fetchone()
                    referrer_new_count = cnt_row[0] if cnt_row else 0
                    counted_referrer_id = referrer_id

            await db.commit()
            return (not was_verified), counted_referrer_id, referrer_new_count, credited_to_contest

    async def handle_user_unsubscribed(self, user_id: int) -> Tuple[bool, Optional[int], int]:
        """
        Foydalanuvchi kanal yoki guruhdan chiqib ketganda jarima qo'llash.
        Agar taklifchiga ball berilgan bo'lsa, -1 ball chegiriladi.
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
                    SELECT id, status, is_contest_credit FROM referrals
                    WHERE referred_id = ? AND referrer_id = ?
                """, (user_id, referrer_id))
                ref_row = await ref_cur.fetchone()

                if ref_row and ref_row[1] == 'confirmed':
                    ref_id_pk = ref_row[0]
                    was_contest_credit = bool(ref_row[2])

                    await db.execute("UPDATE referrals SET status = 'unsubscribed' WHERE id = ?", (ref_id_pk,))

                    if was_contest_credit:
                        await db.execute("""
                            UPDATE users
                            SET referral_count = MAX(0, referral_count - 1),
                                contest_referrals = MAX(0, contest_referrals - 1)
                            WHERE user_id = ?
                        """, (referrer_id,))
                    else:
                        await db.execute("""
                            UPDATE users
                            SET referral_count = MAX(0, referral_count - 1)
                            WHERE user_id = ?
                        """, (referrer_id,))

                    cnt_cur = await db.execute("SELECT contest_referrals FROM users WHERE user_id = ?", (referrer_id,))
                    cnt_row = await cnt_cur.fetchone()
                    referrer_new_count = cnt_row[0] if cnt_row else 0
                    deducted_referrer_id = referrer_id

            await db.commit()
            return was_verified, deducted_referrer_id, referrer_new_count

    # ================= TANLOV VA AVTOMATIK BOSHQARUV =================

    async def get_active_contest(self) -> Optional[Dict[str, Any]]:
        """
        Tanlov holatini o'qiydi va Toshkent vaqti bo'yicha real hisoblaydi.
        Holatlar:
        - 'upcoming': Hali boshlanmagan (countdown boshlanishiga qarab)
        - 'running': Faol (countdown tugashiga qarab)
        - 'ended': Yakunlangan
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM contests ORDER BY id DESC LIMIT 1")
            row = await cursor.fetchone()
            if not row:
                return None

            data = dict(row)
            start_dt = make_tashkent_aware(datetime.fromisoformat(data["start_date"]))
            end_dt = make_tashkent_aware(datetime.fromisoformat(data["end_date"]))
            now_dt = get_tashkent_now()

            # Haqiqiy holatni aniqlash
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

                # Holat o'zgargan bo'lsa, bazada yangilaymiz
                if calculated_status != data["status"]:
                    await db.execute("UPDATE contests SET status = ? WHERE id = ?", (calculated_status, data["id"]))
                    await db.commit()
                    data["status"] = calculated_status
            else:
                data["time_left_str"] = "🏁 Tanlov yakunlandi"
                data["state_badge"] = "🏁 Yakunlangan"

            return data

    async def sync_contest_status(self) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Background scheduler uchun: vaqtni tekshiradi,
        avtomatik 'running' ga o'tkazadi yoki 'ended' qilib g'oliblarni aniqlaydi.
        Qaytaradi: (action_name, contest_dict)
        """
        contest = await self.get_active_contest()
        if not contest:
            return None, None

        cid = contest["id"]
        status = contest["status"]

        if status == "ended":
            # G'oliblar hisoblanganmi tekshiramiz
            async with aiosqlite.connect(self.db_path) as db:
                c_cur = await db.execute("SELECT COUNT(*) FROM winners WHERE contest_id = ?", (cid,))
                w_count = (await c_cur.fetchone())[0]
                if w_count == 0:
                    winners = await self.finalize_contest_and_record_winners(cid)
                    return "finalized", contest

        return None, contest

    async def get_leaderboard(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Reyting ro'yxati.
        Har bir ishtirokchiga kamida 20 ta taklif talabi bo'yicha da'vogarlik (is_eligible) hisoblanadi.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT user_id, username, full_name, contest_referrals, referral_count
                FROM users
                WHERE is_verified = 1 AND status = 'active'
                ORDER BY contest_referrals DESC, created_at ASC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = await cursor.fetchall()

            res = []
            for r in rows:
                item = dict(r)
                pts = item["contest_referrals"]
                item["is_eligible"] = (pts >= config.MIN_REFERRALS_FOR_PRIZE)
                item["needed_to_min"] = max(0, config.MIN_REFERRALS_FOR_PRIZE - pts)
                res.append(item)
            return res

    async def get_user_contest_standing(self, user_id: int) -> Dict[str, Any]:
        """
        Foydalanuvchining shaxsiy ko'rsatkichlari:
        - O'rni
        - Valid balli
        - 20 talik talabga yetish uchun qolgan takliflar
        - Da'vogarlik holati
        - Top 3 ga yetish uchun qolgan ball
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT contest_referrals, referral_count, is_verified FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            if not row:
                return {
                    "rank": 0,
                    "contest_referrals": 0,
                    "alltime_referrals": 0,
                    "is_eligible": False,
                    "needed_to_min": config.MIN_REFERRALS_FOR_PRIZE,
                    "diff_to_top3": config.MIN_REFERRALS_FOR_PRIZE
                }

            user_pts = row[0]
            alltime = row[1]

            # O'rinni aniqlash
            rank_cur = await db.execute("""
                SELECT COUNT(*) FROM users
                WHERE contest_referrals > ? AND is_verified = 1 AND status = 'active'
            """, (user_pts,))
            rank = (await rank_cur.fetchone())[0] + 1

            is_eligible = (user_pts >= config.MIN_REFERRALS_FOR_PRIZE)
            needed_to_min = max(0, config.MIN_REFERRALS_FOR_PRIZE - user_pts)

            # Top 3 ga kirish uchun qancha ball kerak
            top3_cur = await db.execute("""
                SELECT contest_referrals FROM users
                WHERE is_verified = 1 AND status = 'active'
                ORDER BY contest_referrals DESC, created_at ASC
                LIMIT 1 OFFSET 2
            """)
            top3_row = await top3_cur.fetchone()
            if top3_row:
                third_score = top3_row[0]
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

    # ================= G'OLIBLARNI ANIQLASH (STRICT 20+ RULE) =================

    async def finalize_contest_and_record_winners(self, contest_id: int) -> List[Dict[str, Any]]:
        """
        Tanlovni yakunlash va qat'iy 20+ taklif talabiga muvofiq g'oliblarni aniqlash.
        MUHIM QOIDA:
        - Kamida 20 ta taklif to'plaganlar orasidangina Top 3 g'oliblar olinadi!
        - Agar faqat 2 kishi 20 taga yetgan bo'lsa, faqat 2 kishiga sovg'a beriladi.
        - 1-19 ta taklif to'plagan hech kimga sovg'a berilmaydi!
        """
        now = get_tashkent_now().isoformat()
        prizes = [config.PRIZE_1, config.PRIZE_2, config.PRIZE_3]

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Tanlovni yakunlangan deb belgilaymiz
            await db.execute("UPDATE contests SET status = 'ended' WHERE id = ?", (contest_id,))

            # G'oliblarni qidirish: faqat contest_referrals >= 20 bo'lganlar!
            cursor = await db.execute("""
                SELECT user_id, username, full_name, contest_referrals
                FROM users
                WHERE contest_referrals >= ? AND is_verified = 1 AND status = 'active'
                ORDER BY contest_referrals DESC, created_at ASC
                LIMIT 3
            """, (config.MIN_REFERRALS_FOR_PRIZE,))
            candidates = [dict(r) for r in await cursor.fetchall()]

            # Eski g'oliblarni o'chirib qayta yozishdan himoyalanamiz
            await db.execute("DELETE FROM winners WHERE contest_id = ?", (contest_id,))

            winners = []
            for idx, c in enumerate(candidates):
                rank = idx + 1
                prize_name = prizes[idx]
                await db.execute("""
                    INSERT INTO winners (contest_id, user_id, rank, referral_count, prize, awarded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (contest_id, c["user_id"], rank, c["contest_referrals"], prize_name, now))

                c["rank"] = rank
                c["prize"] = prize_name
                winners.append(c)

            await db.commit()
            return winners

    async def get_winners(self, contest_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """G'oliblar ro'yxatini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if contest_id:
                cursor = await db.execute("""
                    SELECT w.*, u.username, u.full_name
                    FROM winners w
                    JOIN users u ON w.user_id = u.user_id
                    WHERE w.contest_id = ?
                    ORDER BY w.rank ASC
                """, (contest_id,))
            else:
                cursor = await db.execute("""
                    SELECT w.*, u.username, u.full_name
                    FROM winners w
                    JOIN users u ON w.user_id = u.user_id
                    ORDER BY w.id DESC LIMIT 3
                """)
            return [dict(r) for r in await cursor.fetchall()]

    # ================= ADMIN FUNKSIYALARI VA CSV EXPORT =================

    async def get_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            total_users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            verified_users = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")).fetchone())[0]
            confirmed_refs = (await (await db.execute("SELECT COUNT(*) FROM referrals WHERE status = 'confirmed'")).fetchone())[0]

            today_str = get_tashkent_now().strftime("%Y-%m-%d")
            today_users = (await (await db.execute("SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (f"{today_str}%",))).fetchone())[0]

            # 20 taga yetgan qatnashchilar soni
            eligible_users = (await (await db.execute("SELECT COUNT(*) FROM users WHERE contest_referrals >= ?", (config.MIN_REFERRALS_FOR_PRIZE,))).fetchone())[0]

            return {
                "total_users": total_users,
                "verified_users": verified_users,
                "today_users": today_users,
                "total_referrals": confirmed_refs,
                "eligible_users": eligible_users
            }

    async def get_global_stats(self) -> Dict[str, Any]:
        return await self.get_stats()

    async def get_all_active_user_ids(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users WHERE status = 'active'")
            return [r[0] for r in await cursor.fetchall()]

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

    async def get_user_referrals_list(self, user_id: int) -> List[Dict[str, Any]]:
        """Foydalanuvchi taklif qilgan a'zolar ro'yxati (admin tekshiruvi uchun)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT r.referred_id, u.full_name, u.username, r.status, r.is_contest_credit, r.created_at, r.confirmed_at
                FROM referrals r
                LEFT JOIN users u ON r.referred_id = u.user_id
                WHERE r.referrer_id = ?
                ORDER BY r.id DESC
            """, (user_id,))
            return [dict(r) for r in await cursor.fetchall()]

    async def get_suspicious_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT s.*, u.full_name, u.username
                FROM suspicious_logs s
                LEFT JOIN users u ON s.referrer_id = u.user_id
                ORDER BY s.id DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in await cursor.fetchall()]

    async def export_participants_csv(self) -> str:
        """Barcha ishtirokchilar statistikasini CSV formatida tayyorlash"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT user_id, username, full_name, referrer_id, is_verified,
                       contest_referrals, referral_count, status, created_at
                FROM users
                ORDER BY contest_referrals DESC, created_at ASC
            """)
            rows = await cursor.fetchall()

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
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO admin_logs (admin_id, action, details, created_at)
                VALUES (?, ?, ?, ?)
            """, (admin_id, action, details, now))
            await db.commit()

    async def get_admin_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM admin_logs ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in await cursor.fetchall()]

    async def start_new_season_contest(self, duration_days: int = 7) -> Dict[str, Any]:
        """Yangi mavsumni boshlash"""
        now = get_tashkent_now()
        end_time = now + timedelta(days=duration_days)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            last_cur = await db.execute("SELECT MAX(season) FROM contests")
            last_season = (await last_cur.fetchone())[0] or 1
            new_season = last_season + 1

            await db.execute("UPDATE contests SET status = 'ended' WHERE status IN ('upcoming', 'running')")
            await db.execute("UPDATE users SET contest_referrals = 0")

            await db.execute("""
                INSERT INTO contests (season, title, start_date, end_date, prize_1, prize_2, prize_3, min_referrals, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?)
            """, (
                new_season,
                f"UniConnect UZ — {new_season}-MAVSUM {duration_days} DAYS CHALLENGE",
                now.isoformat(),
                end_time.isoformat(),
                config.PRIZE_1,
                config.PRIZE_2,
                config.PRIZE_3,
                config.MIN_REFERRALS_FOR_PRIZE,
                now.isoformat()
            ))
            await db.commit()

            cur = await db.execute("SELECT * FROM contests WHERE status = 'running' ORDER BY id DESC LIMIT 1")
            return dict(await cur.fetchone())
