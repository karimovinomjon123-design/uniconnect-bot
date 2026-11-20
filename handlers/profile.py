import logging
from aiogram import Router, F
from aiogram.types import Message
from database.db import Database

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "📊 Mening profilim")
async def show_profile(message: Message, db: Database):
    user = message.from_user
    user_data = await db.get_user(user.id)
    if not user_data:
        await message.answer("⚠️ Profil ma'lumotlari topilmadi. Qaytadan /start bosing.")
        return

    rank, contest_points, diff_top3 = await db.get_user_contest_rank(user.id)
    alltime_refs = user_data.get("referral_count", 0)
    reg_date = user_data["created_at"][:10] if user_data.get("created_at") else "Noma'lum"

    status_badge = "🟢 Faol" if user_data.get("status") == "active" else "🔴 Cheklangan"
    verification_badge = "✅ Tasdiqlangan" if user_data.get("is_verified") else "⚠️ Qayta a'zo bo'lish kerak"

    text = (
        "👤 <b>Sizning shaxsiy profilingiz:</b>\n\n"
        f"• <b>Ism:</b> {user.full_name}\n"
        f"• <b>Username:</b> @{user.username if user.username else 'mavjud emas'}\n"
        f"• <b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"• <b>Ro'yxatdan o'tgan sana:</b> {reg_date}\n"
        f"• <b>A'zolik holati:</b> {verification_badge}\n"
        f"• <b>Hisob holati:</b> {status_badge}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📈 <b>Tanlovdagi natijalaringiz:</b>\n"
        f"• 🏆 <b>Joriy 7 kunlik tanlov balli:</b> <b>{contest_points} ta do'st</b>\n"
        f"• 🥇 <b>Reytingdagi o'rningiz:</b> <b>#{rank}</b>\n"
        f"• 🌐 <b>Jami barcha takliflaringiz:</b> {alltime_refs} ta\n\n"
        "💡 <i>Ko'proq do'stlaringizni taklif qiling va sovg'ali TOP 3 talikka kiring!</i>"
    )

    await message.answer(text, parse_mode="HTML")
