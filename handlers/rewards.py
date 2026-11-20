import logging
from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from database.db import Database
from keyboards.inline import get_rewards_keyboard, get_subscription_keyboard
from utils.helpers import check_subscription
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🎁 Sovg'alar")
async def show_rewards(message: Message, bot: Bot, db: Database):
    user = message.from_user
    if not await check_subscription(bot, user.id, config.REQUIRED_CHANNEL):
        await message.answer(
            "⚠️ <b>Sovg'alar bo'limini ko'rish uchun avval rasmiy kanalimizga a'zo bo'ling:</b>",
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard(config.REQUIRED_CHANNEL_URL, config.GROUP_URL)
        )
        return

    rewards = await db.get_rewards()
    user_db = await db.get_user(user.id)
    ref_count = user_db["referral_count"] if user_db else 0
    claimed_ids = await db.get_user_claimed_rewards(user.id)

    text = (
        "🎁 <b>UniConnect Rag'batlantirish va Sovg'alar Dasturi</b>\n\n"
        "Do'stlaringizni taklif qiling va har bir bosqichda maxsus sovg'alarga ega bo'ling!\n\n"
        f"📊 <b>Sizning to'plagan takliflaringiz:</b> <b>{ref_count} ta</b>\n\n"
        "📋 <b>Mavjud bosqichlar va sovg'alar:</b>\n"
    )

    for rew in rewards:
        status_icon = "✅" if rew["id"] in claimed_ids else ("🔓" if ref_count >= rew["required_referrals"] else "🔒")
        text += (
            f"\n{status_icon} <b>{rew['required_referrals']} ta do'st:</b> {rew['title']}\n"
            f"   ℹ️ <i>{rew['description']}</i>\n"
        )

    text += "\n👇 <i>Ochilgan sovg'ani qabul qilish uchun quyidagi tugmalardan birini bosing:</i>"

    markup = get_rewards_keyboard(rewards, ref_count, claimed_ids)
    await message.answer(text, parse_mode="HTML", reply_markup=markup)

@router.callback_query(F.data.startswith("claim_"))
async def cb_claim_reward(callback: CallbackQuery, db: Database):
    reward_id = int(callback.data.split("_")[1])
    user = callback.from_user

    success, result = await db.claim_reward(user.id, reward_id)
    if not success:
        await callback.answer(result, show_alert=True)
        return

    await callback.answer("🎉 Sovg'a muvaffaqiyatli qabul qilindi!", show_alert=True)
    await callback.message.answer(
        f"🎉 <b>Tabriklaymiz, {user.full_name}!</b>\n\n"
        f"Siz sovg'ani muvaffaqiyatli qo'lga kiritdingiz!\n\n"
        f"📦 <b>Sovg'a ma'lumotlari:</b>\n{result}",
        parse_mode="HTML"
    )

    # Menyu holatini yangilash
    rewards = await db.get_rewards()
    user_db = await db.get_user(user.id)
    ref_count = user_db["referral_count"] if user_db else 0
    claimed_ids = await db.get_user_claimed_rewards(user.id)
    markup = get_rewards_keyboard(rewards, ref_count, claimed_ids)
    try:
        await callback.message.edit_reply_markup(reply_markup=markup)
    except Exception:
        pass

@router.callback_query(F.data.startswith("locked_"))
async def cb_locked_reward(callback: CallbackQuery, db: Database):
    reward_id = int(callback.data.split("_")[1])
    user = callback.from_user
    user_db = await db.get_user(user.id)
    ref_count = user_db["referral_count"] if user_db else 0

    rewards = await db.get_rewards()
    reward = next((r for r in rewards if r["id"] == reward_id), None)
    if reward:
        diff = reward["required_referrals"] - ref_count
        await callback.answer(
            f"🔒 Ushbu sovg'ani ochish uchun yana {diff} ta do'stingizni taklif qilishingiz kerak!",
            show_alert=True
        )
    else:
        await callback.answer("Sovg'a topilmadi.", show_alert=True)

@router.callback_query(F.data.startswith("reward_info_"))
async def cb_reward_info(callback: CallbackQuery):
    await callback.answer("✅ Siz bu sovg'ani allaqachon qabul qilgansiz!", show_alert=True)
