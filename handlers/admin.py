import asyncio
import logging
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_tashkent_now
from database.backup import create_json_backup
from keyboards.inline import (
    get_admin_keyboard,
    get_admin_contest_menu_keyboard,
    get_confirm_keyboard,
    get_broadcast_confirm_keyboard
)
from keyboards.reply import get_cancel_keyboard, get_main_keyboard
from utils.helpers import format_user_mention
import config

logger = logging.getLogger(__name__)
router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    confirm_broadcast = State()
    waiting_for_search_query = State()

def is_admin(user_id: int | str | None) -> bool:
    return config.is_admin(user_id)

@router.message(Command("admin"))
@router.message(F.text == "⚙️ Admin Panel")
async def show_admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ <b>Kirish taqiqlandi!</b>\n\n"
            "Ushbu bo'lim faqat tizim administratorlari uchun mo'ljallangan.",
            parse_mode="HTML"
        )
        return

    text = (
        "⚙️ <b>UniConnect UZ — Administrator Boshqaruv Paneli</b>\n\n"
        "Quyidagi boshqaruv bo'limlaridan birini tanlang:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_keyboard())

# ================= STATISTIKA =================

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    stats = await db.get_stats()
    contest = await db.get_active_contest()

    c_name = contest["title"] if contest else config.COMPETITION_NAME
    c_status = contest["state_badge"] if contest else "Noma'lum"
    time_info = contest["time_left_str"] if contest else "-"
    s_date = contest["start_date"][:16].replace("T", " ") if contest else "-"
    e_date = contest["end_date"][:16].replace("T", " ") if contest else "-"

    text = (
        "📊 <b>Loyiha va Tanlov Statistikasi:</b>\n\n"
        f"🎯 <b>Tanlov:</b> {c_name}\n"
        f"📌 <b>Holat:</b> {c_status}\n"
        f"⏱ <b>Vaqt:</b> <code>{time_info}</code>\n"
        f"📅 <b>Jadval:</b> {s_date} — {e_date} (Asia/Tashkent)\n\n"
        "👥 <b>Foydalanuvchilar:</b>\n"
        f"• Jami ro'yxatdan o'tganlar: <code>{stats['total_users']}</code> ta\n"
        f"• Kanal va guruhda tasdiqlanganlar: <code>{stats['verified_users']}</code> ta\n"
        f"• Bugun qo'shilganlar: <code>{stats['today_users']}</code> ta\n\n"
        "🔗 <b>Referral ko'rsatkichlari:</b>\n"
        f"• Jami tasdiqlangan valid takliflar: <code>{stats['total_referrals']}</code> ta\n"
        f"• 20+ talabni bajargan da'vogarlar soni: <b>{stats['eligible_users']}</b> ta"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    await callback.answer()

# ================= TOP 20 ISHTIROKCHILAR =================

@router.callback_query(F.data == "admin_top")
async def cb_admin_top(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    top_users = await db.get_leaderboard(limit=20)
    lines = [
        "🏆 <b>Top 20 Ishtirokchilar Ro'yxati:</b>\n",
        f"<i>Minimal chegara: {config.MIN_REFERRALS_FOR_PRIZE} ta</i>\n"
    ]

    if not top_users:
        lines.append("<i>Hozircha ishtirokchilar mavjud emas.</i>")
    else:
        for idx, u in enumerate(top_users):
            mention = format_user_mention(u["user_id"], u["full_name"], u["username"])
            pts = u["contest_referrals"]
            elig = "✅ [Da'vogar]" if u["is_eligible"] else f"❌ [{pts}/{config.MIN_REFERRALS_FOR_PRIZE}]"
            lines.append(f"{idx+1}. {mention} (ID: <code>{u['user_id']}</code>) — <b>{pts}</b> ball {elig}")

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=get_admin_keyboard(), disable_web_page_preview=True)
    await callback.answer()

# ================= CSV EKSPORT =================

@router.callback_query(F.data == "admin_export_csv")
async def cb_export_csv(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    await callback.answer("CSV fayl tayyorlanmoqda...")
    csv_data = await db.export_participants_csv()
    csv_bytes = csv_data.encode("utf-8-sig")  # Excel da to'g'ri ochilishi uchun UTF-8 BOM

    filename = f"uniconnect_users_{get_tashkent_now().strftime('%Y%m%d_%H%M')}.csv"
    input_file = BufferedInputFile(csv_bytes, filename=filename)

    await callback.message.answer_document(
        document=input_file,
        caption="📥 <b>UniConnect UZ — Ishtirokchilar to'liq statistikasi (CSV)</b>\n\nFaylni Excel yoki Google Sheets dasturida ochishingiz mumkin.",
        parse_mode="HTML"
    )
    await db.log_admin_action(callback.from_user.id, "EXPORT_CSV", f"Fayl: {filename}")

# ================= JSON BAZA ZAXIRASI (BACKUP) =================

@router.callback_query(F.data == "admin_export_backup")
async def cb_export_backup(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    await callback.answer("To'liq zaxira nusxasi (JSON) tayyorlanmoqda...")
    json_data = await create_json_backup(db)
    json_bytes = json_data.encode("utf-8")

    filename = f"uniconnect_full_backup_{get_tashkent_now().strftime('%Y%m%d_%H%M%S')}.json"
    input_file = BufferedInputFile(json_bytes, filename=filename)

    await callback.message.answer_document(
        document=input_file,
        caption=(
            "💾 <b>UniConnect UZ — Ma'lumotlar Bazasi To'liq Zaxirasi (JSON)</b>\n\n"
            "Ushbu fayl barcha foydalanuvchilar, referrallar, tanlov sozlamalari va loglarni o'z ichiga oladi."
        ),
        parse_mode="HTML"
    )
    await db.log_admin_action(callback.from_user.id, "EXPORT_JSON_BACKUP", f"Fayl: {filename}")

# ================= SHUBHALI FAOLLIKNI KO'RISH =================

@router.callback_query(F.data == "admin_suspicious")
async def cb_admin_suspicious(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    logs = await db.get_suspicious_logs(limit=25)
    lines = ["⚠️ <b>Shubhali Faollik Loglari (Anti-Cheat):</b>\n"]

    if not logs:
        lines.append("<i>Shubhali holatlar aniqlanmagan. Tizim xavfsiz holatda.</i>")
    else:
        for item in logs:
            ref_name = format_user_mention(item["referrer_id"], item.get("full_name") or "Foydalanuvchi", item.get("username"))
            lines.append(
                f"• Taklifchi: {ref_name} (ID: <code>{item['referrer_id']}</code>)\n"
                f"  Sabab: <code>{item['reason']}</code>\n"
                f"  Vaqt: {item['created_at'][:19]}\n"
            )

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=get_admin_keyboard(), disable_web_page_preview=True)
    await callback.answer()

# ================= QIDIRUV VA REFERRAL DETALLARI =================

@router.callback_query(F.data == "admin_search")
async def cb_admin_search(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_search_query)
    await callback.message.answer(
        "🔍 Tekshirmoqchi bo'lgan foydalanuvchining <b>Telegram ID</b> raqamini yoki <b>@username</b>ini yuboring:\n\n"
        "<i>Bekor qilish uchun «❌ Bekor qilish» tugmasini bosing.</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_search_query)
async def process_search_query(message: Message, state: FSMContext, db: Database):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_main_keyboard(is_admin=is_admin(message.from_user.id)))
        return

    query = message.text.strip()
    user_info = await db.search_user(query)

    if not user_info:
        await message.answer("❌ Bunday foydalanuvchi topilmadi. Qayta kiriting yoki bekor qiling:")
        return

    await state.clear()
    uid = user_info["user_id"]
    standing = await db.get_user_contest_standing(uid)
    referrals_list = await db.get_user_referrals_list(uid)

    is_elig = "HA ✅ (20+ bajarilgan)" if standing["is_eligible"] else f"YO'Q ❌ ({standing['contest_referrals']}/{config.MIN_REFERRALS_FOR_PRIZE})"

    lines = [
        "👤 <b>Foydalanuvchi To'liq Ma'lumotlari:</b>\n",
        f"• <b>Ism:</b> {user_info['full_name']}",
        f"• <b>Username:</b> @{user_info['username'] or 'mavjud emas'}",
        f"• <b>Telegram ID:</b> <code>{uid}</code>",
        f"• <b>Taklifchisi:</b> <code>{user_info['referrer_id'] or 'Yo\'q'}</code>",
        f"• <b>Kanal a'zoligi:</b> {'Tasdiqlangan ✅' if user_info['is_verified'] else 'Chiqib ketgan ❌'}",
        f"• <b>Holati:</b> {user_info['status']}",
        f"• <b>Tanlovdagi valid balli:</b> <b>{standing['contest_referrals']} ta</b>",
        f"• <b>Reytingdagi o'rni:</b> #{standing['rank']}",
        f"• <b>Sovg'aga da'vogarlik:</b> <b>{is_elig}</b>",
        f"• <b>Jami barcha takliflari:</b> {user_info['referral_count']} ta",
        f"• <b>Ro'yxatdan o'tgan:</b> {user_info['created_at'][:19]}\n",
        f"📋 <b>Taklif qilgan a'zolari (so'nggi {min(len(referrals_list), 10)} ta):</b>"
    ]

    if not referrals_list:
        lines.append("<i>Hali hech kimni taklif qilmagan.</i>")
    else:
        for r in referrals_list[:10]:
            name = r['full_name'] or f"ID: {r['referred_id']}"
            status_ico = "✅" if r['status'] == 'confirmed' else ("⚠️" if r['status'] == 'unsubscribed' else "⏳")
            credit_str = " (Tanlovga hisoblangan)" if r['is_contest_credit'] else ""
            lines.append(f"• {status_ico} {name} (ID: <code>{r['referred_id']}</code>) — {r['status']}{credit_str}")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=get_main_keyboard(is_admin=is_admin(message.from_user.id)))

# ================= TANLOVNI BOSHQARISH VA TASDIQLASH =================

@router.callback_query(F.data == "admin_contest_menu")
async def cb_contest_menu(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    contest = await db.get_active_contest()
    c_status = contest["status"] if contest else "unknown"
    c_badge = contest["state_badge"] if contest else "-"

    text = (
        "⚙️ <b>Tanlovni Boshqarish Paneli:</b>\n\n"
        f"🎯 <b>Tanlov:</b> {contest.get('title') if contest else '-'}\n"
        f"📌 <b>Hozirgi holat:</b> {c_badge}\n"
        f"⏱ <b>Vaqt:</b> <code>{contest.get('time_left_str') if contest else '-'}</code>\n\n"
        "Kerakli amalni tanlang (barcha muhim amallar xatolikdan saqlash uchun tasdiq so'raydi):"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_contest_menu_keyboard(c_status))
    await callback.answer()

@router.callback_query(F.data == "ask_start_contest")
async def cb_ask_start(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return
    await callback.message.edit_text(
        "⚠️ <b>Haqiqatan ham tanlovni muddatidan oldin HOZIR faollashtirmoqchimisiz?</b>\n\n"
        "Faollashtirilgach, yangi tasdiqlangan takliflar tanlov hisobiga qo'shila boshlaydi.",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard("start_contest_now")
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_start_contest_now")
async def cb_confirm_start(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    contest = await db.get_active_contest()
    if contest:
        await db.set_contest_status(contest["id"], "running")

        await db.log_admin_action(callback.from_user.id, "MANUAL_START_CONTEST", f"Contest ID: {contest['id']}")
        await callback.message.edit_text(
            "🚀 <b>Tanlov muvaffaqiyatli faollashtirildi!</b>\n\nIshtirokchilarning takliflari tanlov hisobiga yozila boshladi.",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )
    await callback.answer("Faollashtirildi!")

@router.callback_query(F.data == "ask_end_contest")
async def cb_ask_end(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return
    await callback.message.edit_text(
        "⚠️ <b>Tanlovni hozir yakunlab, g'oliblarni aniqlashni tasdiqlaysizmi?</b>\n\n"
        f"G'oliblar qat'iy ravishda kamida <b>{config.MIN_REFERRALS_FOR_PRIZE} ta valid taklif</b> to'plaganlar orasidan tanlanadi.",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard("end_contest_now")
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_end_contest_now")
async def cb_confirm_end(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    contest = await db.get_active_contest()
    if not contest:
        await callback.answer("Faol tanlov topilmadi.", show_alert=True)
        return

    winners = await db.finalize_contest_and_record_winners(contest["id"])
    await db.log_admin_action(callback.from_user.id, "MANUAL_END_CONTEST", f"Contest ID: {contest['id']}, G'oliblar: {len(winners)}")

    lines = [
        "🏁 <b>Tanlov Muvaffaqiyatli Yakunlandi!</b>\n",
        f"🎯 <b>Tanlov:</b> {contest['title']}\n",
        f"🏆 <b>ANIQLANGAN G'OLIBLAR (Minimal {config.MIN_REFERRALS_FOR_PRIZE} ta talabi asosida):</b>"
    ]

    if not winners:
        lines.append(f"\n<i>Hech kim minimal {config.MIN_REFERRALS_FOR_PRIZE} ta valid taklif chegarasini bajara olmadi. Sovg'alar berilmadi.</i>")
    else:
        for idx, w in enumerate(winners):
            mention = format_user_mention(w["user_id"], w["full_name"], w["username"])
            lines.append(
                f"\n🏅 <b>{idx+1}-O'RIN:</b> {mention}\n"
                f"• Sovg'a: <b>{w['prize']}</b>\n"
                f"• Ball: <b>{w['contest_referrals']} ta valid taklif</b>\n"
                f"• ID: <code>{w['user_id']}</code>"
            )

    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=get_admin_keyboard(), disable_web_page_preview=True)
    await callback.answer("Tanlov yakunlandi va g'oliblar qayd etildi!")

@router.callback_query(F.data == "ask_new_season")
async def cb_ask_new_season(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return
    await callback.message.edit_text(
        "⚠️ <b>Yangi 7 kunlik mavsumni boshlashni tasdiqlaysizmi?</b>\n\n"
        "Eski tanlov yopiladi, barcha foydalanuvchilarning tanlov ballari 0 dan boshlanadi (tarixiy ballar saqlanadi).",
        parse_mode="HTML",
        reply_markup=get_confirm_keyboard("start_new_season")
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_start_new_season")
async def cb_confirm_new_season(callback: CallbackQuery, db: Database):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return

    new_contest = await db.start_new_season_contest(duration_days=7)
    await db.log_admin_action(callback.from_user.id, "START_NEW_SEASON", f"Season: {new_contest['season']}")

    await callback.message.edit_text(
        f"🚀 <b>Yangi {new_contest['season']}-Mavsum boshlandi!</b>\n\n"
        f"• <b>Tanlov:</b> {new_contest['title']}\n"
        f"• <b>Tugash vaqti:</b> {new_contest['end_date'][:16].replace('T', ' ')} (Asia/Tashkent)\n\n"
        "Barcha ishtirokchilar ballari yangi mavsum uchun 0 ga tenglashtirildi.",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer("Yangi mavsum boshlandi!")

@router.callback_query(F.data == "cancel_action")
@router.callback_query(F.data == "admin_back")
async def cb_admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return
    text = (
        "⚙️ <b>UniConnect UZ — Administrator Boshqaruv Paneli</b>\n\n"
        "Quyidagi boshqaruv bo'limlaridan birini tanlang:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_keyboard())
    await callback.answer()

# ================= BROADCAST =================

@router.callback_query(F.data == "admin_broadcast")
async def cb_start_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
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
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Xabar tarqatish bekor qilindi.", reply_markup=get_main_keyboard(is_admin=is_admin(message.from_user.id)))
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
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
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
        reply_markup=get_main_keyboard(is_admin=is_admin(callback.from_user.id))
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
            await asyncio.sleep(0.04)  # Flood limit himoyasi
        except Exception:
            blocked += 1

    await status_msg.edit_text(
        "✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"• Muvaffaqiyatli yetkazildi: <b>{sent} ta</b>\n"
        f"• Yetkazilmadi / Bloklangan: <b>{blocked} ta</b>\n"
        f"• Jami: <b>{total_users} ta</b>",
        parse_mode="HTML"
    )
    await db.log_admin_action(callback.from_user.id, "BROADCAST", f"Yuborildi: {sent}, Bloklandi: {blocked}")

@router.callback_query(AdminStates.confirm_broadcast, F.data == "broadcast_cancel")
async def cb_cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("❌ Xabar tarqatish bekor qilindi.")
    await callback.answer()

@router.callback_query(F.data == "admin_close")
async def cb_admin_close(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat berilmagan! Siz administrator emassiz.", show_alert=True)
        return
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("Panel yopildi.")
