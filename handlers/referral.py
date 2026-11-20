import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from database.db import Database
from keyboards.inline import get_referral_share_keyboard

logger = logging.getLogger(__name__)
router = Router()

async def get_referral_content(bot: Bot, user_id: int, db: Database):
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    contest = await db.get_active_contest()
    contest_title = contest["title"] if contest else "UniConnect Marafon-Tanlovi"
    time_left = contest["time_left_str"] if contest else "Faol"

    rank, contest_points, diff_top3 = await db.get_user_contest_rank(user_id)
    user_db = await db.get_user(user_id)
    alltime_refs = user_db.get("referral_count", 0) if user_db else 0

    text = (
        f"👥 <b>Do'stlarni taklif qilish va Sovg'alar yutish</b>\n\n"
        f"🎯 <b>Tanlov:</b> {contest_title}\n"
        f"⏳ <b>Qolgan vaqt:</b> <code>{time_left}</code>\n\n"
        "🔗 <b>Sizning shaxsiy taklif havolangiz:</b>\n"
        f"<code>{ref_link}</code>\n"
        "👆 <i>Ustiga bir marta bossangiz, havola avtomatik nusxalanadi!</i>\n\n"
        "📊 <b>Sizning ko'rsatkichlaringiz:</b>\n"
        f"• 🏆 <b>Tanlovdagi ballingiz:</b> <b>{contest_points} ta do'st</b>\n"
        f"• 📈 <b>Reytingdagi o'rningiz:</b> <b>#{rank}</b>\n"
        f"• 🌐 <b>Jami barcha takliflaringiz:</b> {alltime_refs} ta\n\n"
        "💡 <b>Qoidalar:</b>\n"
        "1. Do'stingiz botga kirib, rasmiy kanal va guruhimizga a'zo bo'lgandagina sizga <b>+1 ball</b> qo'shiladi.\n"
        "2. Agar taklif qilingan a'zo guruh yoki kanaldan chiqib ketsa, hisobingizdan ball chegiriladi (adolatli tanlov uchun).\n"
        "3. Tanlov yakunida g'oliblar uchun maxsus sovg'alar rasmiy kanalda e'lon qilinadi va taqdim etiladi! 🎁"
    )

    markup = get_referral_share_keyboard(bot_username, user_id)
    return text, markup

@router.message(F.text == "👥 Do'stlarni taklif qilish")
async def show_referral(message: Message, bot: Bot, db: Database):
    text, markup = await get_referral_content(bot, message.from_user.id, db)
    await message.answer(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

@router.callback_query(F.data == "open_referral")
async def cb_open_referral(callback: CallbackQuery, bot: Bot, db: Database):
    text, markup = await get_referral_content(bot, callback.from_user.id, db)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(F.data == "refresh_referral")
async def cb_refresh_referral(callback: CallbackQuery, bot: Bot, db: Database):
    text, markup = await get_referral_content(bot, callback.from_user.id, db)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        await callback.answer("🔄 Ma'lumotlaringiz yangilandi!")
    except Exception:
        await callback.answer("Eng so'nggi natijalar aks etmoqda.")
