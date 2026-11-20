from aiogram import Router, F
from aiogram.types import Message
from keyboards.inline import get_contact_keyboard
import config

router = Router()

@router.message(F.text == "ℹ️ Loyiha haqida")
async def show_about(message: Message):
    text = (
        "🌟 <b>UniConnect — O'zbekiston Talabalari Hamjamiyati</b>\n\n"
        "<b>Bizning asosiy maqsadimiz:</b>\n"
        "O'zbekistondagi turli oliy o'quv yurtlari talabalarini yagona, do'stona va faol platformada birlashtirish, "
        "o'zaro muloqot, networking, tajriba almashish va katta imkoniyatlar yaratishdan iborat!\n\n"
        "📌 <b>Bizning rasmiy sahifalarimiz:</b>\n"
        f"• 📢 <b>Telegram Kanal:</b> <a href='{config.REQUIRED_CHANNEL_URL}'>{config.REQUIRED_CHANNEL}</a>\n"
        f"• 💬 <b>Telegram Guruh:</b> <a href='{config.REQUIRED_GROUP_URL}'>{config.REQUIRED_GROUP}</a>\n"
        f"• 📸 <b>Instagram:</b> <a href='{config.INSTAGRAM_URL}'>@uniconnect_uz</a>\n\n"
        "🚀 Hamjamiyatimizga qo'shiling va kelajakni birgalikda quramiz!"
    )
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

@router.message(F.text == "📞 Bog'lanish")
async def show_contact(message: Message):
    text = (
        "📞 <b>UniConnect — Bog'lanish va Ma'muriyat</b>\n\n"
        "Savol, taklif, shikoyat yoki hamkorlik bo'yicha biz bilan bemalol bog'lanishingiz mumkin:\n\n"
        f"• 👤 <b>Bosh Administrator:</b> <a href='{config.SUPPORT_ADMIN_URL}'>{config.SUPPORT_ADMIN}</a>\n"
        f"• 📞 <b>Telefon raqam:</b> <code>{config.SUPPORT_PHONE}</code>\n"
        f"• 📢 <b>Rasmiy Kanal:</b> <a href='{config.REQUIRED_CHANNEL_URL}'>{config.REQUIRED_CHANNEL}</a>\n"
        f"• 💬 <b>Rasmiy Guruh:</b> <a href='{config.REQUIRED_GROUP_URL}'>{config.REQUIRED_GROUP}</a>\n\n"
        "Biz har doim talabalarni qo'llab-quvvatlashdan mamnunmiz! 😊"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_contact_keyboard(), disable_web_page_preview=True)
