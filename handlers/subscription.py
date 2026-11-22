import logging
from aiogram import Router, Bot, F
from aiogram.types import CallbackQuery
from database.db import Database
from keyboards.reply import get_main_keyboard
from utils.helpers import check_all_subscriptions
import config

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery, bot: Bot, db: Database):
    user = callback.from_user
    is_all_ok, missing = await check_all_subscriptions(bot, user.id)

    if not is_all_ok:
        missing_names = ", ".join([item[1] for item in missing])
        await callback.answer(
            f"Siz hali quyidagi sahifalarga a'zo bo'lmadingiz:\n{missing_names}\n\nIltimos, a'zo bo'lib qayta tekshiring!",
            show_alert=True
        )
        return

    await callback.answer("A'zoligingiz tasdiqlandi!", show_alert=False)

    # Referralni tasdiqlash
    _, ref_id, new_count, credited_to_contest = await db.verify_user_and_confirm_referral(user.id)
    if ref_id and ref_id != user.id:
        try:
            contest_note = "🏆 <b>Tanlov hisobingizga +1 ball qo'shildi!</b>" if credited_to_contest else "ℹ️ <i>(Tanlov boshlangach ballar tanlov hisobiga yoziladi)</i>"
            await bot.send_message(
                chat_id=ref_id,
                text=(
                    f"🎉 <b>Tabriklaymiz!</b>\n\n"
                    f"Sizning taklif havolangiz orqali <b>{user.full_name}</b> a'zolikni tasdiqladi.\n"
                    f"{contest_note}\n"
                    f"Tanlovdagi joriy ballingiz: <b>{new_count} ta</b>."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Taklifchiga xabar yetkazishda xato: {e}")

    is_admin = user.id in config.ADMIN_IDS
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "A'zoligingiz muvaffaqiyatli tasdiqlandi!\n\n"
        f"🏆 <b>{config.COMPETITION_NAME}</b> da ishtirok etish uchun shaxsiy taklif havolangizdan foydalaning.\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_admin=is_admin)
    )
