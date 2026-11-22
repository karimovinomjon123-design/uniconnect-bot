import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from database.db import Database
from utils.helpers import format_user_mention
from keyboards.inline import get_leaderboard_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()

MEDALS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
PAGE_SIZE = 10

async def build_leaderboard_view(user_id: int, db: Database, page: int = 1):
    contest = await db.get_active_contest()
    c_title = contest["title"] if contest else config.COMPETITION_NAME
    time_info = contest["time_left_str"] if contest else "Faol"

    offset = (page - 1) * PAGE_SIZE
    top_users = await db.get_leaderboard(limit=PAGE_SIZE, offset=offset)

    # Jami ishtirokchilar soni sahifalash uchun
    async with db as _:
        pass
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        total_p_cur = await conn.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1 AND status = 'active'")
        total_participants = (await total_p_cur.fetchone())[0]

    total_pages = max(1, (total_participants + PAGE_SIZE - 1) // PAGE_SIZE)
    standing = await db.get_user_contest_standing(user_id)

    user_rank = standing["rank"]
    user_pts = standing["contest_referrals"]
    user_eligible = standing["is_eligible"]
    needed_to_min = standing["needed_to_min"]

    lines = [
        f"🏆 <b>{c_title}</b>\n",
        f"⏱ <b>Vaqt:</b> <code>{time_info}</code>",
        f"⚠️ <b>Sovg'aga da'vogarlik talabi:</b> Kamida <b>{config.MIN_REFERRALS_FOR_PRIZE} ta valid a'zo</b>\n",
        f"📊 <b>YETAKCHILAR RO'YXATI (Sahifa {page}/{total_pages}):</b>"
    ]

    if not top_users:
        lines.append("<i>Hozircha ishtirokchilar ro'yxati shakllanmagan.</i>")
    else:
        for idx, u in enumerate(top_users):
            actual_rank = offset + idx + 1
            if actual_rank <= 10:
                medal = MEDALS[actual_rank - 1]
            else:
                medal = f"{actual_rank}."

            name = format_user_mention(u["user_id"], u["full_name"], u["username"])
            pts = u["contest_referrals"]

            # Da'vogarlik belgisi
            if u["is_eligible"]:
                elig_badge = "✅ [Da'vogar]"
            else:
                elig_badge = f"❌ [{pts}/{config.MIN_REFERRALS_FOR_PRIZE}]"

            lines.append(f"{medal} <b>{name}</b> — <b>{pts}</b> ta {elig_badge}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("👤 <b>SIZNING KO'RSATKICHLARINGIZ:</b>")
    lines.append(f"• O'rningiz: <b>#{user_rank}</b>")
    lines.append(f"• Tanlovdagi valid takliflaringiz: <b>{user_pts} ta</b>")

    if user_eligible:
        lines.append("• Holat: ✅ <b>Sovg'aga to'liq da'vogarsiz!</b> (Top 3 ga kirishga harakat qiling)")
    else:
        lines.append(f"• Holat: ❌ <b>Da'vogar emassiz</b> (Kamida 20 ta kerak. Yana <b>{needed_to_min} ta</b> yetishmayapti)")

    markup = get_leaderboard_keyboard(page=page, total_pages=total_pages)
    return "\n".join(lines), markup

@router.message(F.text == "🏆 Reyting")
@router.message(F.text == "🏆 Reyting (Top 10)")
async def show_leaderboard(message: Message, db: Database):
    text, markup = await build_leaderboard_view(message.from_user.id, db, page=1)
    await message.answer(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

@router.callback_query(F.data == "refresh_leaderboard")
async def cb_refresh_leaderboard(callback: CallbackQuery, db: Database):
    text, markup = await build_leaderboard_view(callback.from_user.id, db, page=1)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        await callback.answer("Reyting yangilandi!")
    except Exception:
        await callback.answer("Eng so'nggi ma'lumotlar.")

@router.callback_query(F.data.startswith("leaderboard_page_"))
async def cb_leaderboard_page(callback: CallbackQuery, db: Database):
    page_num = int(callback.data.split("_")[2])
    text, markup = await build_leaderboard_view(callback.from_user.id, db, page=page_num)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        await callback.answer()
    except Exception:
        await callback.answer()

@router.callback_query(F.data == "ignore")
async def cb_ignore(callback: CallbackQuery):
    await callback.answer()
