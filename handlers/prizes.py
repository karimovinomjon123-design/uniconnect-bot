import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🎁 Sovg'alar")
async def show_prizes(message: Message):
    text = (
        f"🎁 <b>{config.COMPETITION_NAME} Sovg'alari</b>\n\n"
        "Tanlov yakunida eng ko'p valid taklif to'plagan g'oliblarga quyidagi sovrinlar topshiriladi:\n\n"
        f"🥇 <b>1-O'RIN:</b> <b>{config.PRIZE_1}</b>\n"
        f"🥈 <b>2-O'RIN:</b> <b>{config.PRIZE_2}</b>\n"
        f"🥉 <b>3-O'RIN:</b> <b>{config.PRIZE_3}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <b>ENG MUHIM QOIDA: MINIMAL 20 TA TAKLIF TALABI!</b>\n\n"
        f"Sovringa da'vogar bo'lish uchun har bir ishtirokchi kamida <b>{config.MIN_REFERRALS_FOR_PRIZE} ta valid a'zo</b> taklif qilishi shart:\n\n"
        "• <b>1–19 ta taklif:</b> Sovg'aga da'vogar bo'la olmaydi ❌\n"
        "• <b>20 va undan ortiq taklif:</b> Sovg'aga to'liq da'vogar ✅\n\n"
        "📌 <i>Eslatma: Faqat minimal 20 talik chegarani zabt etgan ishtirokchilargina g'olib deb e'lon qilinadi. "
        "Agar faqat 2 kishi 20 tadan oshsa, faqat 2 kishiga sovg'a beriladi. "
        "20 taga yetmagan hech kimga sovg'a berilmaydi.</i>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Taklif havolamni olish", callback_data="open_referral")],
        [InlineKeyboardButton(text="🏆 Reytingni ko'rish", callback_data="refresh_leaderboard")]
    ])

    await message.answer(text, parse_mode="HTML", reply_markup=markup)
