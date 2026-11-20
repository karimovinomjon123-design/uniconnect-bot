import os
import unittest
from pathlib import Path
from database.db import Database

class TestUniConnectBot(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_db_path = Path("test_uniconnect_v2.db")
        if self.test_db_path.exists():
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass
        self.db = Database(self.test_db_path)
        await self.db.init_db()

    async def asyncTearDown(self):
        if self.test_db_path.exists():
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    async def test_user_registration_and_duplicate(self):
        is_new = await self.db.add_user(1001, "student1", "Ali Valiyev")
        self.assertTrue(is_new)

        u = await self.db.get_user(1001)
        self.assertEqual(u["full_name"], "Ali Valiyev")
        self.assertEqual(u["contest_referrals"], 0)

        # Duplicate
        is_new_again = await self.db.add_user(1001, "student1_up", "Ali Valiyev 2")
        self.assertFalse(is_new_again)

    async def test_referral_retention_and_unsubscribe_penalty(self):
        # User A
        await self.db.add_user(1001, "usera", "Foydalanuvchi A")
        # User B joined via User A
        await self.db.add_user(1002, "userb", "Foydalanuvchi B", referrer_id=1001)

        user_a = await self.db.get_user(1001)
        self.assertEqual(user_a["contest_referrals"], 0)

        # User B verified membership in channel & group
        verified, ref_id, new_score = await self.db.verify_user_and_confirm_referral(1002)
        self.assertTrue(verified)
        self.assertEqual(ref_id, 1001)
        self.assertEqual(new_score, 1)

        user_a_after = await self.db.get_user(1001)
        self.assertEqual(user_a_after["contest_referrals"], 1)

        # User B unsubs / leaves channel!
        was_ver, ded_ref, score_after_ded = await self.db.handle_user_unsubscribed(1002)
        self.assertTrue(was_ver)
        self.assertEqual(ded_ref, 1001)
        self.assertEqual(score_after_ded, 0)

        user_a_ded = await self.db.get_user(1001)
        self.assertEqual(user_a_ded["contest_referrals"], 0)

        # User B rejoins and re-verifies!
        re_ver, re_ref, re_score = await self.db.verify_user_and_confirm_referral(1002)
        self.assertTrue(re_ver)
        self.assertEqual(re_ref, 1001)
        self.assertEqual(re_score, 1)

        user_a_restored = await self.db.get_user(1001)
        self.assertEqual(user_a_restored["contest_referrals"], 1)

    async def test_top3_contest_lifecycle(self):
        contest = await self.db.get_active_contest()
        self.assertIsNotNone(contest)
        self.assertEqual(contest["season"], 1)

        # 4 users
        for uid in [1, 2, 3, 4]:
            await self.db.add_user(uid, f"u{uid}", f"User {uid}")
            await self.db.verify_user_and_confirm_referral(uid)

        import aiosqlite
        async with aiosqlite.connect(self.test_db_path) as conn:
            await conn.execute("UPDATE users SET contest_referrals = 15 WHERE user_id = 1")
            await conn.execute("UPDATE users SET contest_referrals = 25 WHERE user_id = 2")
            await conn.execute("UPDATE users SET contest_referrals = 10 WHERE user_id = 3")
            await conn.execute("UPDATE users SET contest_referrals = 5 WHERE user_id = 4")
            await conn.commit()

        top = await self.db.get_leaderboard(limit=10)
        self.assertEqual(top[0]["user_id"], 2)  # 1st place: 25 pts
        self.assertEqual(top[1]["user_id"], 1)  # 2nd place: 15 pts
        self.assertEqual(top[2]["user_id"], 3)  # 3rd place: 10 pts
        self.assertEqual(top[3]["user_id"], 4)  # 4th place: 5 pts

        # User 4 needs 6 points to enter Top 3 (10 - 5 + 1 = 6)
        rank4, pts4, diff4 = await self.db.get_user_contest_rank(4)
        self.assertEqual(rank4, 4)
        self.assertEqual(pts4, 5)
        self.assertEqual(diff4, 6)

        # End contest
        ended_c, winners = await self.db.end_contest_and_get_winners(contest["id"])
        self.assertEqual(len(winners), 3)
        self.assertEqual(winners[0]["user_id"], 2)

        # Start new contest (Season 2)
        new_c = await self.db.start_new_contest(duration_days=7)
        self.assertEqual(new_c["season"], 2)

        # All contest_referrals reset to 0 for season 2
        u2 = await self.db.get_user(2)
        self.assertEqual(u2["contest_referrals"], 0)

if __name__ == "__main__":
    unittest.main()
