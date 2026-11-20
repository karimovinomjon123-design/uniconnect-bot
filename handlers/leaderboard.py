import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database.db import Database
from utils.helpers import format_user_mention
from keyboards.inline import get_leaderboard_keyboard

logger = logging.getLogger(__name__)
router = Router()

MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

async def build_leaderboard_text(user_id: int, db: Database) -> str:
    contest = await db.get_active_contest()
    contest_title = contest["title"] if contest else "UniConnect Marafon-Tanlovi"
    time_left = contest["time_left_str"] if contest else "Faol"

    top_users = await db.get_leaderboard(limit=10)
    user_rank, user_points, diff_top3 = await db.get_user_contest_rank(user_id)

    p1 = contest.get("prize_1") if contest else "🥇 1-o'rin: Bosh sovrin"
    p2 = contest.get("prize_2") if contest else "🥈 2-o'rin: 2-darajali sovrin"
    p3 = contest.get("prize_3") if contest else "🥉 3-o'rin: Maxsus Merch to'plami"

    lines = [
        f"🏆 <b>UniConnect — Marafon Reytingi va Sovg'alar</b>\n",
        f"🎯 <b>Tanlov:</b> {contest_title}",
        f"⏳ <b>Qolgan vaqt:</b> <code>{time_left}</code>\n",
        "🎁 <b>TOP 3 SOVG'ALARI:</b>",
        f"{p1}",
        f"{p2}",
        f"{p3}\n",
        "━━━━━━━━━━━━━━━━━━━━",
        "📊 <b>HOZIRGI YETAKCHILAR RO'YXATI (TOP 10):</b>"
    ]

    if not top_users:
        lines.append("<i>Hozircha yetakchilar ro'yxati shakllanmagan. Siz birinchi bo'lishingiz mumkin!</i>")
    else:
        for idx, u in enumerate(top_users):
            medal = MEDALS[idx] if idx < len(MEDALS) else f"{idx+1}."
            name = format_user_mention(u["user_id"], u["full_name"], u["username"])
            lines.append(f"{medal} <b>{name}</b> — <code>{u['contest_referrals']}</code> ta do'st")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("👤 <b>SIZNING NATIJANGIZ:</b>")
    lines.append(f"• O'rningiz: <b>#{user_rank}</b>")
    lines.append(f"• To'plagan ballingiz: <b>{user_points} ta do'st</b>")

    if user_rank <= 3 and user_points > 0:
        lines.append(f"🎉 <b>Ajoyib! Siz hozirda sovg'ali TOP 3 o'rindasiz! O'rningizni saqlab qoling!</b>")
    else:
        lines.append(f"🎯 Sovg'ali <b>TOP 3</b> talikka kirish uchun yana kamida <b>{diff_top3} ta</b> do'st taklif qilishingiz kerak!")

    return "\n".join(lines)

@router.message(F.text == "🏆 Reyting va Sovg'alar (Top 3)")
async def show_leaderboard(message: Message, db: Database):
    text = await build_leaderboard_text(message.from_user.id, db)
    await message.answer(text, parse_mode="HTML", reply_markup=get_leaderboard_keyboard(), disable_web_page_preview=True)

@router.callback_query(F.data == "refresh_leaderboard")
async def cb_refresh_leaderboard(callback: CallbackQuery, db: Database):
    text = await build_leaderboard_text(callback.from_user.id, db)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_leaderboard_keyboard(), disable_web_page_preview=True)
        await callback.answer("🔄 Reyting yangilandi!")
    except Exception:
        await callback.answer("Natijalar yangilangan.")
