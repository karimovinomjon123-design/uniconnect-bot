import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import Database
import config

logger = logging.getLogger(__name__)
router = Router()

async def build_stats_text(user_id: int, db: Database) -> str:
    user_db = await db.get_user(user_id)
    if not user_db:
        return "⚠️ Foydalanuvchi ma'lumotlari topilmadi. Qaytadan /start bosing."

    standing = await db.get_user_contest_standing(user_id)
    contest = await db.get_active_contest()

    pts = standing["contest_referrals"]
    alltime = standing["alltime_referrals"]
    rank = standing["rank"]
    is_eligible = standing["is_eligible"]
    needed_to_min = standing["needed_to_min"]
    diff_to_top3 = standing["diff_to_top3"]

    c_title = contest["title"] if contest else config.COMPETITION_NAME
    time_left = contest["time_left_str"] if contest else "Noma'lum"
    c_status = contest["state_badge"] if contest else "Faol"

    if is_eligible:
        eligibility_badge = "✅ <b>Sovg'aga da'vogarsiz!</b> (20+ talabi bajarilgan)"
        threshold_info = "Tabriklaymiz, siz minimal 20 talik talabni bajargansiz! Endi Top 3 o'rinni egallashga harakat qiling."
    else:
        eligibility_badge = f"❌ <b>Sovg'aga da'vogar emassiz</b> ({pts}/{config.MIN_REFERRALS_FOR_PRIZE})"
        threshold_info = f"Sovg'aga da'vogar bo'lish uchun yana kamida <b>{needed_to_min} ta</b> do'stingizni taklif qilishingiz kerak."

    text = (
        "📊 <b>Sizning Shaxsiy Statistikangiz</b>\n\n"
        f"🎯 <b>Tanlov:</b> {c_title}\n"
        f"📌 <b>Tanlov holati:</b> {c_status}\n"
        f"⏳ <b>Vaqt:</b> <code>{time_left}</code>\n\n"
        "📈 <b>Tanlovdagi ko'rsatkichlaringiz:</b>\n"
        f"• 👥 Valid takliflaringiz: <b>{pts} ta</b>\n"
        f"• 🏆 Reytingdagi o'rningiz: <b>#{rank}</b>\n"
        f"• 🌐 Barcha takliflaringiz (tarix): {alltime} ta\n\n"
        f"🛡 <b>Da'vogarlik holati:</b>\n{eligibility_badge}\n"
        f"ℹ️ {threshold_info}\n\n"
        f"🎯 Top 3 sovg'ali o'ringa kirish uchun yana kamida: <b>{diff_to_top3} ta</b> taklif kerak."
    )
    return text

def get_stats_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔗 Taklif havolam", callback_data="open_referral"),
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_stats")
        ]
    ])

@router.message(F.text == "📊 Mening statistikam")
async def show_stats(message: Message, db: Database):
    text = await build_stats_text(message.from_user.id, db)
    await message.answer(text, parse_mode="HTML", reply_markup=get_stats_inline_keyboard())

@router.callback_query(F.data == "refresh_stats")
async def cb_refresh_stats(callback: CallbackQuery, db: Database):
    text = await build_stats_text(callback.from_user.id, db)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_stats_inline_keyboard())
        await callback.answer("Statistika yangilandi!")
    except Exception:
        await callback.answer("Eng so'nggi ma'lumotlar.")
