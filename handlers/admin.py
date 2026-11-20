import asyncio
import logging
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database
from keyboards.inline import get_admin_keyboard, get_broadcast_confirm_keyboard
from keyboards.reply import get_cancel_keyboard, get_main_keyboard
from utils.helpers import format_user_mention
import config

logger = logging.getLogger(__name__)
router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    confirm_broadcast = State()
    waiting_for_search_query = State()

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.message(Command("admin"))
@router.message(F.text == "⚙️ Admin Panel")
async def show_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return

    text = (
        "⚙️ <b>UniConnect — Administrator Paneli</b>\n\n"
        "Quyidagi boshqaruv bo'limlaridan birini tanlang:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        return

    stats = await db.get_stats()
    contest = await db.get_active_contest()
    contest_info = contest['title'] if contest else "Faol tanlov yo'q"
    time_info = contest['time_left_str'] if contest else "-"

    text = (
        "📊 <b>UniConnect — Loyiha Statistikasi:</b>\n\n"
        f"• 👥 <b>Jami ro'yxatdan o'tganlar:</b> <code>{stats['total_users']}</code> ta\n"
        f"• ✅ <b>Kanal va guruhda tasdiqlanganlar:</b> <code>{stats['verified_users']}</code> ta\n"
        f"• 📅 <b>Bugun qo'shilganlar:</b> <code>{stats['today_users']}</code> ta\n"
        f"• 🔗 <b>Tasdiqlangan barcha takliflar:</b> <code>{stats['total_referrals']}</code> ta\n\n"
        f"🎯 <b>Joriy Tanlov:</b> {contest_info}\n"
        f"⏳ <b>Qolgan vaqt:</b> <code>{time_info}</code>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_top")
async def cb_admin_top(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        return

    top_users = await db.get_leaderboard(limit=20)
    lines = ["🏆 <b>Joriy Tanlov Yetakchilari (Top 20):</b>\n"]
    if not top_users:
        lines.append("<i>Hozircha ishtirokchilar yo'q.</i>")
    else:
        for idx, u in enumerate(top_users):
            mention = format_user_mention(u["user_id"], u["full_name"], u["username"])
            lines.append(f"{idx+1}. {mention} (ID: <code>{u['user_id']}</code>) — <b>{u['contest_referrals']}</b> ball (Jami: {u['referral_count']})")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=get_admin_keyboard(), disable_web_page_preview=True)
    await callback.answer()

# ================= TANLOVNI BOSHQARISH =================

@router.callback_query(F.data == "admin_end_contest")
async def cb_admin_end_contest(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        return

    contest = await db.get_active_contest()
    if not contest:
        await callback.answer("Hozirda faol tanlov mavjud emas!", show_alert=True)
        return

    ended_contest, winners = await db.end_contest_and_get_winners(contest["id"])

    lines = [
        "🏁 <b>Marafoni yakunlandi va G'oliblar aniqlandi!</b>\n",
        f"🎯 <b>Tanlov:</b> {ended_contest['title']}\n",
        "🏆 <b>G'OLIBLAR (TOP 3):</b>"
    ]

    medals = ["🥇 1-O'RIN", "🥈 2-O'RIN", "🥉 3-O'RIN"]
    if not winners:
        lines.append("<i>Hech qanday g'olib aniqlanmadi.</i>")
    else:
        for idx, w in enumerate(winners[:3]):
            mention = format_user_mention(w["user_id"], w["full_name"], w["username"])
            lines.append(f"\n{medals[idx]}: {mention}")
            lines.append(f"• ID: <code>{w['user_id']}</code>")
            lines.append(f"• To'plagan balli: <b>{w['contest_referrals']} ta do'st</b>")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 <i>G'oliblar bilan bog'lanib, sovg'alarini topshirishingiz mumkin.</i>")
    lines.append("<i>Yangi tanlov boshlash uchun «🚀 Yangi 7 kunlik tanlov» tugmasini bosing.</i>")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=get_admin_keyboard(), disable_web_page_preview=True)
    await callback.answer("Tanlov yakunlandi!")

@router.callback_query(F.data == "admin_new_contest")
async def cb_admin_new_contest(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        return

    new_contest = await db.start_new_contest(duration_days=7)
    text = (
        "🚀 <b>Yangi 7 Kunlik Marafon-Konkurs muvaffaqiyatli boshlandi!</b>\n\n"
        f"• <b>Mavsum:</b> {new_contest['season']}-Mavsum\n"
        f"• <b>Nomi:</b> {new_contest['title']}\n"
        f"• <b>Tugash vaqti:</b> {new_contest['end_date'][:16].replace('T', ' ')} (UTC)\n\n"
        "Barcha ishtirokchilarning tanlov ballari 0 dan boshlandi. Bosh sovrinlar uchun kurash boshlandi!"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    await callback.answer("Yangi 7 kunlik tanlov yoqildi!", show_alert=True)

# ================= QIDIRUV =================

@router.callback_query(F.data == "admin_search")
async def cb_admin_search(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_search_query)
    await callback.message.answer(
        "🔍 Foydalanuvchining <b>Telegram ID</b> raqamini yoki <b>@username</b>ini kiriting:\n\n"
        "<i>Bekor qilish uchun «❌ Bekor qilish» tugmasini bosing.</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_search_query)
async def process_search_query(message: Message, state: FSMContext, db: Database):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_keyboard(is_admin=True))
        return

    query = message.text.strip()
    user_info = await db.search_user(query)

    if not user_info:
        await message.answer("❌ Bunday foydalanuvchi ma'lumotlar bazasidan topilmadi. Qayta urinib ko'ring yoki bekor qiling:")
        return

    await state.clear()
    rank, points, _ = await db.get_user_contest_rank(user_info["user_id"])
    text = (
        "👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"• <b>Ism:</b> {user_info['full_name']}\n"
        f"• <b>Username:</b> @{user_info['username'] or 'mavjud emas'}\n"
        f"• <b>Telegram ID:</b> <code>{user_info['user_id']}</code>\n"
        f"• <b>Taklifchisi (Referrer):</b> <code>{user_info['referrer_id'] or 'Yo\'q'}</code>\n"
        f"• <b>A'zolik holati:</b> {'Tasdiqlangan ✅' if user_info['is_verified'] else 'Chiqib ketgan / Tasdiqlanmagan ❌'}\n"
        f"• <b>Tanlovdagi balli:</b> <b>{user_info['contest_referrals']} ta</b>\n"
        f"• <b>Tanlovdagi o'rni:</b> #{rank}\n"
        f"• <b>Jami barcha takliflari:</b> {user_info['referral_count']} ta\n"
        f"• <b>Holati:</b> {user_info['status']}\n"
        f"• <b>Ro'yxatdan o'tgan:</b> {user_info['created_at'][:19]}\n"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(is_admin=True))

# ================= BROADCAST =================

@router.callback_query(F.data == "admin_broadcast")
async def cb_start_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.message.answer(
        "📢 <b>Barcha foydalanuvchilarga xabar yuborish</b>\n\n"
        "Tarqatmoqchi bo'lgan xabaringizni yuboring (matn, rasm, video yoki post ko'rinishida):\n\n"
        "<i>Bekor qilish uchun «❌ Bekor qilish» tugmasini bosing.</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Xabar tarqatish bekor qilindi.", reply_markup=get_main_keyboard(is_admin=True))
        return

    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    await state.set_state(AdminStates.confirm_broadcast)

    await message.answer(
        "⚠️ <b>Xabar barcha faol foydalanuvchilarga yuborilishini tasdiqlaysizmi?</b>",
        parse_mode="HTML",
        reply_markup=get_broadcast_confirm_keyboard()
    )

@router.callback_query(AdminStates.confirm_broadcast, F.data == "broadcast_confirm")
async def cb_confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    if not is_admin(callback.from_user.id):
        return

    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    await state.clear()

    user_ids = await db.get_all_active_user_ids()
    total_users = len(user_ids)

    status_msg = await callback.message.answer(
        f"🚀 Xabar tarqatish boshlandi... Jami qabul qiluvchilar: <b>{total_users} ta</b>.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_admin=True)
    )

    sent = 0
    blocked = 0

    for uid in user_ids:
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            sent += 1
            await asyncio.sleep(0.04)  # Telegram flood limit himoyasi
        except Exception:
            blocked += 1

    await status_msg.edit_text(
        "✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"• Muvaffaqiyatli yetkazildi: <b>{sent} ta</b>\n"
        f"• Yetkazilmadi / Bloklangan: <b>{blocked} ta</b>\n"
        f"• Jami: <b>{total_users} ta</b>",
        parse_mode="HTML"
    )

@router.callback_query(AdminStates.confirm_broadcast, F.data == "broadcast_cancel")
async def cb_cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Xabar tarqatish bekor qilindi.")
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("Panel yopildi.")
