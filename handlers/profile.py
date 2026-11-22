import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import Database
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "👤 Mening profilim")
@router.message(F.text == "📊 Mening profilim")
async def show_profile(message: Message, db: Database):
    user = message.from_user
    user_data = await db.get_user(user.id)
    if not user_data:
        await message.answer("⚠️ Profil ma'lumotlari topilmadi. Qaytadan /start bosing.")
        return

    standing = await db.get_user_contest_standing(user.id)
    alltime_refs = user_data.get("referral_count", 0)
    contest_refs = standing["contest_referrals"]
    rank = standing["rank"]
    is_eligible = standing["is_eligible"]

    reg_date = user_data["created_at"][:10] if user_data.get("created_at") else "Noma'lum"
    status_badge = "🟢 Faol" if user_data.get("status") == "active" else "🔴 Cheklangan"
    verification_badge = "✅ Tasdiqlangan" if user_data.get("is_verified") else "⚠️ Qayta a'zo bo'lish kerak"
    elig_str = "✅ Da'vogar (20+ bajarilgan)" if is_eligible else f"❌ Da'vogar emas ({contest_refs}/{config.MIN_REFERRALS_FOR_PRIZE})"

    text = (
        "👤 <b>Sizning Shaxsiy Profilingiz</b>\n\n"
        f"• <b>Ism:</b> {user.full_name}\n"
        f"• <b>Username:</b> @{user.username if user.username else 'mavjud emas'}\n"
        f"• <b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"• <b>A'zolik holati:</b> {verification_badge}\n"
        f"• <b>Hisob holati:</b> {status_badge}\n"
        f"• <b>Ro'yxatdan o'tgan:</b> {reg_date}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>{config.COMPETITION_NAME}:</b>\n"
        f"• Tanlovdagi valid ballingiz: <b>{contest_refs} ta</b>\n"
        f"• Reytingdagi o'rningiz: <b>#{rank}</b>\n"
        f"• Sovg'aga da'vogarlik: <b>{elig_str}</b>\n"
        f"• Jami barcha takliflaringiz: {alltime_refs} ta"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Taklif havolam", callback_data="open_referral"),
            InlineKeyboardButton(text="📊 To'liq statistika", callback_data="refresh_stats")
        ]
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=markup)
