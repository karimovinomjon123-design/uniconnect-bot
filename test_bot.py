import os
import unittest
from pathlib import Path
from datetime import datetime, timedelta
import aiosqlite

from database.db import Database
import config

class TestUniConnectBotComprehensive(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_db_path = Path("test_uniconnect_challenge.db")
        if self.test_db_path.exists():
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass
        self.db = Database(self.test_db_path, force_sqlite=True)
        await self.db.init_db()

    async def asyncTearDown(self):
        if self.test_db_path.exists():
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    async def test_01_user_registration_and_anti_duplicate(self):
        """Yangi foydalanuvchini qo'shish va takroriy kirishlarni tekshirish"""
        is_new = await self.db.add_user(1001, "student1", "Ali Valiyev")
        self.assertTrue(is_new, "Yangi foydalanuvchi True qaytarishi kerak")

        u = await self.db.get_user(1001)
        self.assertEqual(u["full_name"], "Ali Valiyev")
        self.assertEqual(u["contest_referrals"], 0)
        self.assertEqual(u["is_verified"], 0)

        # Takroriy kirish (dublikat oldini olish)
        is_new_again = await self.db.add_user(1001, "student1_updated", "Ali Valiyev Yangi")
        self.assertFalse(is_new_again, "Mavjud foydalanuvchi False qaytarishi kerak")
        u_updated = await self.db.get_user(1001)
        self.assertEqual(u_updated["full_name"], "Ali Valiyev Yangi")

    async def test_02_self_referral_prevention(self):
        """O'ziga o'zi referral bo'lishni bloklash"""
        await self.db.add_user(2001, "self_ref_user", "O'zim", referrer_id=2001)
        u = await self.db.get_user(2001)
        self.assertIsNone(u["referrer_id"], "Self-referral qabul qilinmasligi kerak")

    async def test_03_referral_credit_during_contest_and_unsubscribe_penalty(self):
        """Tanlov vaqtida ball qo'shilishi va a'zolik bekor qilinganda jarima (-1)"""
        # Tanlovni running holatiga keltiramiz
        async with aiosqlite.connect(self.test_db_path) as conn:
            # 7 kunlik faol oraliq o'rnatamiz
            now_dt = datetime.now()
            s_dt = (now_dt - timedelta(days=1)).isoformat()
            e_dt = (now_dt + timedelta(days=6)).isoformat()
            await conn.execute("UPDATE contests SET start_date = ?, end_date = ?, status = 'running' WHERE id = 1", (s_dt, e_dt))
            await conn.commit()

        # Foydalanuvchi A (taklifchi)
        await self.db.add_user(3001, "usera", "Foydalanuvchi A")
        # Foydalanuvchi B (A orqali kelgan)
        await self.db.add_user(3002, "userb", "Foydalanuvchi B", referrer_id=3001)

        # B a'zo bo'ldi va tasdiqlandi
        is_new_v, ref_id, new_score, is_credited = await self.db.verify_user_and_confirm_referral(3002)
        self.assertTrue(is_new_v)
        self.assertEqual(ref_id, 3001)
        self.assertEqual(new_score, 1)
        self.assertTrue(is_credited, "Tanlov vaqtida ball tanlovga yozilishi kerak")

        # B kanaldan chiqib ketdi (-1 ball jarima)
        was_v, ded_ref, score_after_ded = await self.db.handle_user_unsubscribed(3002)
        self.assertTrue(was_v)
        self.assertEqual(ded_ref, 3001)
        self.assertEqual(score_after_ded, 0)

        user_a = await self.db.get_user(3001)
        self.assertEqual(user_a["contest_referrals"], 0)

        # B qayta a'zo bo'ldi va tasdiqladi
        re_v, re_ref, re_score, re_credited = await self.db.verify_user_and_confirm_referral(3002)
        self.assertTrue(re_credited)
        self.assertEqual(re_score, 1)
        user_a_restored = await self.db.get_user(3001)
        self.assertEqual(user_a_restored["contest_referrals"], 1)

    async def test_04_strict_minimum_20_referrals_rule(self):
        """
        QAT'IY QOIDA:
        1-19 ta taklif: Sovrin yo'q (is_eligible = False)
        20+ ta taklif: Sovrin da'vogari (is_eligible = True)
        """
        # 4 nafar ishtirokchi kiritamiz
        # User 1: 25 ta taklif (>= 20 -> Da'vogar)
        # User 2: 21 ta taklif (>= 20 -> Da'vogar)
        # User 3: 19 ta taklif (< 20 -> SOVRIN BERILMAYDI!)
        # User 4: 8 ta taklif (< 20 -> SOVRIN BERILMAYDI!)
        async with aiosqlite.connect(self.test_db_path) as conn:
            for uid, name, pts in [(4001, "Ulug'bek", 25), (4002, "Nodir", 21), (4003, "Sardor", 19), (4004, "Kamron", 8)]:
                await conn.execute("""
                    INSERT INTO users (user_id, username, full_name, is_verified, contest_referrals, referral_count, status, created_at)
                    VALUES (?, ?, ?, 1, ?, ?, 'active', datetime('now'))
                """, (uid, f"user_{uid}", name, pts, pts))
            await conn.commit()

        # Leaderboard tekshiruvi
        lb = await self.db.get_leaderboard(limit=10)
        self.assertEqual(len(lb), 4)
        self.assertEqual(lb[0]["user_id"], 4001)
        self.assertTrue(lb[0]["is_eligible"])
        self.assertEqual(lb[0]["needed_to_min"], 0)

        self.assertEqual(lb[1]["user_id"], 4002)
        self.assertTrue(lb[1]["is_eligible"])
        self.assertEqual(lb[1]["needed_to_min"], 0)

        # 3-o'rindagi Sardorda 19 ta taklif, u da'vogar EMAS!
        self.assertEqual(lb[2]["user_id"], 4003)
        self.assertFalse(lb[2]["is_eligible"], "19 ta taklif bilan sovrin olishi mumkin emas!")
        self.assertEqual(lb[2]["needed_to_min"], 1, "20 taga yetish uchun yana 1 ta taklif kerak")

        # Shaxsiy ko'rsatkich
        st3 = await self.db.get_user_contest_standing(4003)
        self.assertEqual(st3["rank"], 3)
        self.assertFalse(st3["is_eligible"])
        self.assertEqual(st3["needed_to_min"], 1)

        # Tanlovni yakunlash va g'oliblarni aniqlash
        winners = await self.db.finalize_contest_and_record_winners(1)
        
        # Sardorda 19 ta bo'lgani sababli u g'oliblar ro'yxatiga KIRMAYDI!
        # Faqat 2 ta kishi 20 dan oshgan, shuning uchun FAQAT 2 TA G'OLIB bo'lishi shart!
        self.assertEqual(len(winners), 2, "Faqat 20 dan oshgan 2 kishigagina sovg'a berilishi shart")
        self.assertEqual(winners[0]["user_id"], 4001)
        self.assertEqual(winners[0]["rank"], 1)
        self.assertIn("Premium", winners[0]["prize"])

        self.assertEqual(winners[1]["user_id"], 4002)
        self.assertEqual(winners[1]["rank"], 2)
        self.assertIn("50,000", winners[1]["prize"])

    async def test_05_csv_export_and_admin_logs(self):
        """Admin CSV eksporti va shubhali harakatlar jurnali"""
        # User qo'shamiz
        await self.db.add_user(5001, "adm_tester", "Admin Test")
        await self.db.log_admin_action(8786525548, "test_action", "Tizim tekshiruvi")

        csv_str = await self.db.export_participants_csv()
        self.assertIn("Telegram ID,Username", csv_str)
        self.assertIn("5001", csv_str)

        logs = await self.db.get_admin_logs(limit=5)
        self.assertTrue(len(logs) >= 1)
        self.assertEqual(logs[0]["admin_id"], 8786525548)

    async def test_06_json_backup(self):
        """Ma'lumotlar bazasining JSON zaxira nusxasini tekshirish"""
        from database.backup import create_json_backup
        await self.db.add_user(6001, "backup_tester", "Backup Test Foydalanuvchisi")
        backup_str = await create_json_backup(self.db)
        self.assertIn("UniConnect UZ Telegram Bot", backup_str)
        self.assertIn("6001", backup_str)

    async def test_07_active_participants_count_and_context_manager(self):
        """Yangi get_active_participants_count va context manager interfeysini tekshirish"""
        async with self.db as managed_db:
            self.assertEqual(managed_db, self.db)

        await self.db.add_user(7001, "act1", "Active 1")
        await self.db.add_user(7002, "act2", "Active 2")
        await self.db.verify_user_and_confirm_referral(7001)
        await self.db.verify_user_and_confirm_referral(7002)

        count = await self.db.get_active_participants_count()
        self.assertTrue(count >= 2)

if __name__ == "__main__":
    unittest.main()
