import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from database.db import Database
from keyboards.inline import get_referral_share_keyboard
import config

logger = logging.getLogger(__name__)
router = Router()

async def get_referral_content(bot: Bot, user_id: int, db: Database):
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    contest = await db.get_active_contest()
    contest_title = contest["title"] if contest else config.COMPETITION_NAME
    time_left = contest["time_left_str"] if contest else "Faol"

    standing = await db.get_user_contest_standing(user_id)
    contest_points = standing["contest_referrals"]
    rank = standing["rank"]
    is_eligible = standing["is_eligible"]
    needed_to_min = standing["needed_to_min"]

    status_str = "✅ Sovg'aga da'vogar" if is_eligible else f"❌ Da'vogar emas (yana {needed_to_min} ta kerak)"

    text = (
        f"🔗 <b>Shaxsiy Taklif Havolangiz</b>\n\n"
        f"🎯 <b>Tanlov:</b> {contest_title}\n"
        f"⏳ <b>Vaqt:</b> <code>{time_left}</code>\n\n"
        "Do'stlaringizni taklif qilish uchun quyidagi havolani yuboring:\n"
        f"<code>{ref_link}</code>\n"
        "👆 <i>Ustiga bir marta bossangiz, havola avtomatik nusxalanadi.</i>\n\n"
        "📊 <b>Ko'rsatkichlaringiz:</b>\n"
        f"• Tanlovdagi ballingiz: <b>{contest_points} ta do'st</b>\n"
        f"• Reytingdagi o'rningiz: <b>#{rank}</b>\n"
        f"• Da'vogarlik holati: <b>{status_str}</b>\n\n"
        "⚠️ <b>Muhim qoidalar:</b>\n"
        "1. Do'stingiz botga kirib, rasmiy kanal va guruhga a'zo bo'lgandagina <b>+1 valid ball</b> hisoblanadi.\n"
        "2. Agar taklif qilingan a'zo guruh yoki kanaldan chiqib ketsa, hisobingizdan ball chegiriladi.\n"
        "3. Sovg'aga da'vogar bo'lish uchun kamida <b>20 ta valid referral</b> to'plashingiz shart!"
    )

    markup = get_referral_share_keyboard(bot_username, user_id)
    return text, markup

@router.message(F.text == "🔗 Taklif havolam")
@router.message(F.text == "👥 Do'stlarni taklif qilish")
async def show_referral(message: Message, bot: Bot, db: Database):
    text, markup = await get_referral_content(bot, message.from_user.id, db)
    await message.answer(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

@router.callback_query(F.data == "open_referral")
async def cb_open_referral(callback: CallbackQuery, bot: Bot, db: Database):
    text, markup = await get_referral_content(bot, callback.from_user.id, db)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
    await callback.answer()
