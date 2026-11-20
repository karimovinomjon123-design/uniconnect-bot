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

    # Foydalanuvchini bazaga qo'shish
    is_new = await db.add_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        referrer_id=referrer_id
    )

    if is_new:
        logger.info(f"Yangi foydalanuvchi: {user.id} (@{user.username}), taklifchi: {referrer_id}")

    # Barcha majburiy kanal va guruhlarni tekshiramiz
    is_all_ok, missing = await check_all_subscriptions(bot, user.id)

    if not is_all_ok:
        welcome_text = (
            f"👋 <b>Assalomu alaykum, {user.full_name}!</b>\n\n"
            "🌟 <b>UniConnect</b> — O'zbekiston talabalari hamjamiyatining rasmiy botiga xush kelibsiz!\n\n"
            "🚀 <b>Hozirda 7 kunlik katta talabalar marafon-konkursi o'tkazilmoqda!</b>\n"
            "🎁 G'oliblar uchun maxsus sovg'alar rasmiy kanalimiz orqali e'lon qilinadi!\n\n"
            "⚠️ <b>Botdan to'liq foydalanish, do'stlaringizni taklif qilish va tanlovda qatnashish uchun "
            "rasmiy kanal va guruhimizga a'zo bo'ling:</b>"
        )
        await message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(),
            disable_web_page_preview=True
        )
        return

    # Agar a'zo bo'lsa, tasdiqlaymiz va referralni hisoblaymiz
    _, ref_id, new_count = await db.verify_user_and_confirm_referral(user.id)
    if ref_id and ref_id != user.id:
        try:
            await bot.send_message(
                chat_id=ref_id,
                text=(
                    f"🎉 <b>Yangi do'st qo'shildi!</b>\n\n"
                    f"Sizning taklif havolangiz orqali <b>{user.full_name}</b> botga kirdi va barcha sahifalarga a'zo bo'ldi!\n"
                    f"Sizga <b>+1 ball</b> qo'shildi!\n"
                    f"🏆 Tanlovdagi joriy ballingiz: <b>{new_count} ta</b>."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Taklifchiga xabar yuborishda xato: {e}")

    is_admin = user.id in config.ADMIN_IDS
    await message.answer(
        f"👋 <b>Assalomu alaykum, {user.full_name}!</b>\n\n"
        "🎉 <b>UniConnect</b> talabalar platformasiga xush kelibsiz!\n\n"
        "Quyidagi menyu orqali do'stlaringizni taklif qiling, tanlovda ishtirok eting va "
        "qimmatbaho sovg'alarga ega bo'ling 👇",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_admin=is_admin)
    )
