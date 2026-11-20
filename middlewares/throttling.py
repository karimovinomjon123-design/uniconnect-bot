import time
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.6):
        self.rate_limit = rate_limit
        self.last_actions: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            now = time.monotonic()
            last_time = self.last_actions.get(user_id, 0.0)

            if now - last_time < self.rate_limit:
                # Spam / Anti-flood himoyasi
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⚠️ Iltimos, tugmalarni shoshilmasdan bosing!", show_alert=False)
                    except Exception:
                        pass
                return None  # Xabarni qayta ishlamaymiz

            self.last_actions[user_id] = now

        return await handler(event, data)
