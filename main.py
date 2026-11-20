import os
import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database.db import Database
from handlers import register_all_handlers
from middlewares import ThrottlingMiddleware, SubscriptionCheckMiddleware

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("uniconnect_bot")

async def handle_health(request):
    """Bulutli serverlar (Render, Railway, Koyeb) uchun 24/7 tiriklik tekshiruvi"""
    return web.Response(text="UniConnect Bot is active and running 24/7! 🚀", status=200)

async def start_health_server():
    """Agar PORT muhit o'zgaruvchisi berilgan bo'lsa (serverda), health-check web serverni yoqadi"""
    port_env = os.getenv("PORT")
    if not port_env:
        return None
    try:
        port = int(port_env)
        app = web.Application()
        app.router.add_get("/", handle_health)
        app.router.add_get("/health", handle_health)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Bulutli server uchun health-check web server ishga tushdi: port {port}")
        return runner
    except Exception as e:
        logger.warning(f"Health-check serverini yoqishda ogohlantirish: {e}")
        return None

async def main():
    logger.info("UniConnect Telegram Boti ishga tushirilmoqda...")

    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "XATOLIK: BOT_TOKEN ko'rsatilmagan! "
            "Iltimos, .env fayliga BotFather'dan olingan tokenni kiriting."
        )
        return

    # Ma'lumotlar bazasini ishga tushirish va yangilash
    db = Database(config.DB_PATH)
    await db.init_db()
    logger.info(f"SQLite ma'lumotlar bazasi tayyor: {config.DB_PATH}")

    # Server health-check ni yoqish (agar serverda bo'lsa)
    web_runner = await start_health_server()

    # Bot va Dispatcher yaratish
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Dependency Injection
    dp["db"] = db
    dp["bot"] = bot

    # 1. Anti-Flood / Anti-DDoS himoyasi
    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.5))

    # 2. Majburiy a'zolikni qat'iy tekshirish
    dp.message.middleware(SubscriptionCheckMiddleware())
    dp.callback_query.middleware(SubscriptionCheckMiddleware())

    # Handlerlarni ulash
    register_all_handlers(dp)

    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot ulandi: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"Telegramga ulanishda xato: {e}")
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()
        return

    # Eski kutilayotgan yangilanishlarni tozalash
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("UniConnect boti 24/7 faol ishlamoqda. To'xtatish uchun Ctrl+C bosing.")
    try:
        await dp.start_polling(bot)
    finally:
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()
        logger.info("Bot sessiyasi yopildi.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
