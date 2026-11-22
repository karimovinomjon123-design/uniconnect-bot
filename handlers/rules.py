import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "📜 Tanlov qoidalari")
async def show_rules(message: Message):
    text = (
        f"📜 <b>{config.COMPETITION_NAME} — Rasmiy Qoidalari</b>\n\n"
        "<b>1. Muddat va vaqt:</b>\n"
        "• Boshlanish: <b>2026-yil 23-noyabr, 00:00</b> (Asia/Tashkent, UTC+5)\n"
        "• Tugash: <b>2026-yil 29-noyabr, 23:59:59</b> (Asia/Tashkent, UTC+5)\n"
        "• Davomiyligi: Aniq 7 kun.\n\n"
        "<b>2. Qatnashish tartibi:</b>\n"
        "• Har bir ishtirokchi «🔗 Taklif havolam» bo'limidagi o'z shaxsiy havolasi orqali do'stlarini taklif qiladi.\n\n"
        "<b>3. Valid ball hisoblanishi sharti:</b>\n"
        "• Taklif qilingan foydalanuvchi botga kirib, rasmiy kanal va guruhimizga a'zo bo'lgandagina taklifchiga +1 valid ball qo'shiladi.\n"
        "• Agar a'zo guruh yoki kanaldan chiqib ketsa, hisobdan -1 ball chegiriladi.\n\n"
        f"<b>4. Minimal talab (Threshold):</b>\n"
        f"• Sovg'alarga da'vogar bo'lish uchun kamida <b>{config.MIN_REFERRALS_FOR_PRIZE} ta valid a'zo</b> taklif qilish shart.\n"
        "• 1–19 ta taklif bilan sovrinli o'rin egallab bo'lmaydi.\n\n"
        "<b>5. Anti-cheat (Adolatli tanlov):</b>\n"
        "• O'zini o'zi taklif qilish taqiqlanadi.\n"
        "• Bitta Telegram akkaunt faqat bir marta hisoblanadi.\n"
        "• Botlar yoki soxta dasturlar orqali spam qilish qat'iyan taqiqlanadi va admin tomonidan tekshiriladi.\n\n"
        "<b>6. G'oliblarni aniqlash:</b>\n"
        "• 29-noyabr 23:59:59 da tanlov avtomatik to'xtatiladi va eng ko'p valid ball to'plagan Top 3 ishtirokchi g'olib deb e'lon qilinadi."
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Taklif havolamni olish", callback_data="open_referral")],
        [InlineKeyboardButton(text="🎁 Sovg'alarni ko'rish", callback_data="open_prizes")]
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=markup)

@router.callback_query(F.data == "open_prizes")
async def cb_open_prizes(callback):
    from handlers.prizes import show_prizes
    await show_prizes(callback.message)
    await callback.answer()
