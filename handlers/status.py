import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.db import Database
import config

logger = logging.getLogger(__name__)
router = Router()

async def build_status_text(db: Database) -> str:
    contest = await db.get_active_contest()
    stats = await db.get_stats()

    c_title = contest["title"] if contest else config.COMPETITION_NAME
    c_status = contest["state_badge"] if contest else "Faol"
    time_info = contest["time_left_str"] if contest else "Noma'lum"

    s_date = contest["start_date"][:16].replace("T", " ") if contest else "2026-11-23 00:00"
    e_date = contest["end_date"][:16].replace("T", " ") if contest else "2026-11-29 23:59"

    text = (
        "⏳ <b>Tanlov Holati va Vaqt Hisoblagichi</b>\n\n"
        f"🎯 <b>Nomi:</b> {c_title}\n"
        f"📌 <b>Hozirgi holat:</b> {c_status}\n"
        f"⏱ <b>Vaqt hisobi:</b> <code>{time_info}</code>\n\n"
        "📅 <b>Jadval (Asia/Tashkent vaqti):</b>\n"
        f"• Boshlanish: <code>{s_date}</code> (UTC+5)\n"
        f"• Yakunlanish: <code>{e_date}</code> (UTC+5)\n"
        "• Davomiyligi: Aniq 7 kun\n\n"
        "📊 <b>Umumiy ko'rsatkichlar:</b>\n"
        f"• Jami ro'yxatdan o'tganlar: <b>{stats['total_users']} ta</b>\n"
        f"• Kanalda tasdiqlanganlar: <b>{stats['verified_users']} ta</b>\n"
        f"• Jami valid takliflar: <b>{stats['total_referrals']} ta</b>\n"
        f"• 20+ talabni bajargan da'vogarlar: <b>{stats.get('eligible_users', 0)} ta</b>"
    )
    return text

@router.message(F.text == "⏳ Tanlov holati")
async def show_status(message: Message, db: Database):
    text = await build_status_text(db)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_contest_status"),
            InlineKeyboardButton(text="🏆 Reyting", callback_data="refresh_leaderboard")
        ]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=markup)

@router.callback_query(F.data == "refresh_contest_status")
async def cb_refresh_contest_status(callback: CallbackQuery, db: Database):
    text = await build_status_text(db)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_contest_status"),
            InlineKeyboardButton(text="🏆 Reyting", callback_data="refresh_leaderboard")
        ]
    ])
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        await callback.answer("Tanlov holati yangilandi!")
    except Exception:
        await callback.answer("Eng so'nggi holat.")
