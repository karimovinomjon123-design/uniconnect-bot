import html
import logging
from typing import Tuple, List
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import config

logger = logging.getLogger(__name__)

async def check_chat_member(bot: Bot, user_id: int, chat_target: str | int) -> bool:
    """Bitta kanal yoki guruhda a'zolikni tekshirish"""
    try:
        member = await bot.get_chat_member(chat_id=chat_target, user_id=user_id)
        if member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        ):
            return True
        return False
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.warning(f"Kanal/guruh tekshirishda xatolik ({chat_target}, user={user_id}): {e}")
        return False
    except Exception as e:
        logger.error(f"Kutilmagan tekshiruv xatoligi ({chat_target}, user={user_id}): {e}")
        return False

async def check_all_subscriptions(bot: Bot, user_id: int) -> Tuple[bool, List[tuple]]:
    """
    Barcha majburiy kanal va guruhlarni tekshiradi.
    Qaytaradi: (barchasida bormi?, a'zo bo'linmaganlar ro'yxati)
    """
    missing = []
    for chat_target, chat_title, chat_url in config.REQUIRED_CHATS:
        is_member = await check_chat_member(bot, user_id, chat_target)
        if not is_member:
            missing.append((chat_target, chat_title, chat_url))

    return (len(missing) == 0), missing

def format_user_mention(user_id: int, full_name: str, username: str | None = None) -> str:
    """Foydalanuvchi ismini xavfsiz HTML formatda chiqarish"""
    safe_name = html.escape(full_name)
    if username:
        return f'<a href="https://t.me/{username}">{safe_name}</a>'
    return f'<a href="tg://user?id={user_id}">{safe_name}</a>'
