import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from keyboards.inline import get_subscription_keyboard
from utils.helpers import check_all_subscriptions
from database.db import Database
import config

logger = logging.getLogger(__name__)

class SubscriptionCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        bot: Bot = data.get("bot")
        db: Database = data.get("db")

        user_id = None
        message_to_reply = None

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            message_to_reply = event

            # /start komandasi ro'yxatdan o'tish va referral ushlashi uchun middleware'dan o'tishi kerak
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)

        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            message_to_reply = event.message

            # "check_subscription" tugmasi aynan tekshirish uchun xizmat qiladi
            if event.data == "check_subscription":
                return await handler(event, data)

        if not user_id or not bot or not db:
            return await handler(event, data)

        # Adminlar uchun tekshiruv shart emas (istisno)
        if user_id in config.ADMIN_IDS:
            return await handler(event, data)

        # Barcha majburiy kanal va guruhlarni tekshiramiz
        is_all_subscribed, missing_chats = await check_all_subscriptions(bot, user_id)

        if not is_all_subscribed:
            # Foydalanuvchi chiqib ketgan bo'lsa, ballni ayirish
            was_verified, referrer_id, new_count = await db.handle_user_unsubscribed(user_id)
            if was_verified and referrer_id:
                try:
                    await bot.send_message(
                        chat_id=referrer_id,
                        text=(
                            "⚠️ <b>Diqqat!</b>\n\n"
                            f"Siz taklif qilgan do'stingiz rasmiy sahifalarimizdan chiqib ketganligi sababli, "
                            f"sizning hisobingizdan <b>-1 ball</b> chegirildi.\n"
                            f"Joriy konkurs ballingiz: <b>{new_count} ta</b>.\n"
                            "<i>(Do'stingiz qayta a'zo bo'lsa, ballingiz yana tiklanadi).</i>"
                        ),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.warning(f"Taklifchiga unsubs jarimasini yetkazishda xato: {e}")

            warning_text = (
                "⚠️ <b>Diqqat! Siz rasmiy kanalimiz yoki guruhimizdan chiqib ketgansiz!</b>\n\n"
                "UniConnect talabalar hamjamiyati botidan foydalanish, do'stlarni taklif qilish va "
                "<b>Top 3 tanlovida sovg'alar yutish</b> uchun barcha sahifalarimizga a'zo bo'lishingiz shart:\n\n"
            )
            for ch_user, ch_title, ch_url in config.REQUIRED_CHATS:
                warning_text += f"• <a href='{ch_url}'>{ch_title}</a>\n"

            warning_text += "\n<i>A'zo bo'lgach, quyidagi «✅ A'zolikni tekshirish» tugmasini bosing:</i>"

            if isinstance(event, CallbackQuery):
                try:
                    await event.answer("⚠️ Avval kanal va guruhga a'zo bo'ling!", show_alert=True)
                except Exception:
                    pass

            if message_to_reply:
                await message_to_reply.answer(
                    warning_text,
                    parse_mode="HTML",
                    reply_markup=get_subscription_keyboard(),
                    disable_web_page_preview=True
                )
            return None  # Buyruqni to'xtatamiz

        return await handler(event, data)
