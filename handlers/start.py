import logging
from aiogram import Router, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message
from database.db import Database
from keyboards.reply import get_main_keyboard
from keyboards.inline import get_subscription_keyboard
from utils.helpers import check_all_subscriptions
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot, db: Database):
    user = message.from_user
    args = command.args
    referrer_id = None

    # Deep-link referral parametrini tekshirish (/start ref_1234567 yoki /start 1234567)
    if args:
        ref_candidate = args.replace("ref_", "").strip()
        if ref_candidate.isdigit():
            referrer_id = int(ref_candidate)

    # Foydalanuvchini bazaga qo'shish (takroriy ro'yxatdan o'tish tekshiriladi)
    is_new = await db.add_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        referrer_id=referrer_id
    )

    if is_new:
        logger.info(f"Yangi foydalanuvchi: {user.id} (@{user.username}), taklifchi: {referrer_id}")

    # Majburiy kanal va guruh a'zoligini tekshirish
    is_all_ok, missing = await check_all_subscriptions(bot, user.id)

    if not is_all_ok:
        welcome_text = (
            f"Assalomu alaykum, {user.full_name}!\n\n"
            f"🌟 <b>UniConnect UZ</b> platformasining rasmiy botiga xush kelibsiz.\n\n"
            f"🏆 <b>{config.COMPETITION_NAME}</b>\n"
            "📅 <b>Muddat:</b> 23-noyabr 00:00 dan 29-noyabr 23:59:59 gacha (7 kun)\n"
            f"🎁 <b>Bosh sovrin:</b> {config.PRIZE_1}\n"
            "⚠️ <b>Muhim shart:</b> Sovg'aga da'vogar bo'lish uchun kamida <b>20 ta valid referral</b> taklif qilish shart!\n\n"
            "Botdan foydalanish va tanlovda qatnashish uchun rasmiy kanal va guruhimizga a'zo bo'ling:"
        )
        await message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(),
            disable_web_page_preview=True
        )
        return

    # A'zo bo'lsa, referral holatini tasdiqlaymiz
    _, ref_id, new_count, credited_to_contest = await db.verify_user_and_confirm_referral(user.id)
    if ref_id and ref_id != user.id:
        try:
            contest_note = "🏆 <b>Tanlov hisobingizga +1 ball qo'shildi!</b>" if credited_to_contest else "ℹ️ <i>(Tanlov boshlangach ballar tanlov hisobiga yoziladi)</i>"
            await bot.send_message(
                chat_id=ref_id,
                text=(
                    f"🎉 <b>Yangi do'st qo'shildi!</b>\n\n"
                    f"Sizning taklif havolangiz orqali <b>{user.full_name}</b> rasmiy sahifalarimizga a'zo bo'ldi.\n"
                    f"{contest_note}\n"
                    f"Tanlovdagi joriy ballingiz: <b>{new_count} ta</b>."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Taklifchiga xabar yuborishda xato: {e}")

    is_admin = config.is_admin(user.id)
    await message.answer(
        f"Assalomu alaykum, {user.full_name}!\n\n"
        "🌟 <b>UniConnect UZ</b> talabalar hamjamiyatiga xush kelibsiz.\n"
        f"🏆 <b>{config.COMPETITION_NAME}</b> da ishtirok eting va sovg'alarni qo'lga kiriting!\n\n"
        "Quyidagi menyu orqali kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_admin=is_admin)
    )
