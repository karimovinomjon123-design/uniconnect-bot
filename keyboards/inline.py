import urllib.parse
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Barcha majburiy kanallar va guruhlar uchun inline tugmalar"""
    buttons = []
    for chat_target, chat_title, chat_url in config.REQUIRED_CHATS:
        buttons.append([InlineKeyboardButton(text=chat_title, url=chat_url)])

    buttons.append([InlineKeyboardButton(text="✅ A'zolikni tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_referral_share_keyboard(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    """
    Do'stlarga taklif havolasini bitta tugma bilan yuborish.
    URL parametrini xavfsiz URL-encode qilamiz, shunda Telegramda havola
    oddiy matn bo'lib qolmasdan, bosiladigan (kliklanadigan) havola sifatida ochiladi.
    """
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_caption = (
        "👋 Salom! O'zbekiston talabalari hamjamiyati — UniConnect'da 7 kunlik katta marafon boshlandi!\n\n"
        "🎁 Top 3 talabaga qimmatbaho sovg'alar beriladi!\n"
        "Do'stlar orttirish, tajriba almashish va sovg'alarga ega bo'lish uchun siz ham qo'shiling 👇"
    )

    encoded_url = urllib.parse.quote(ref_link, safe="")
    encoded_text = urllib.parse.quote(share_caption, safe="")
    share_url = f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"

    buttons = [
        [InlineKeyboardButton(text="🚀 Do'stlarga va guruhlarga yuborish", url=share_url)],
        [InlineKeyboardButton(text="🔄 Natijamni yangilash", callback_data="refresh_referral")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Reyting oynasidagi tezkor amallar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Taklif havolasini olish", callback_data="open_referral"),
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_leaderboard")
        ]
    ])

def get_contact_keyboard() -> InlineKeyboardMarkup:
    """Bog'lanish bo'limi tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Administrator (@IKN150)", url=config.SUPPORT_ADMIN_URL),
        ],
        [
            InlineKeyboardButton(text="📢 Rasmiy Kanal", url=config.REQUIRED_CHANNEL_URL),
            InlineKeyboardButton(text="💬 Talabalar Guruhi", url=config.REQUIRED_GROUP_URL),
        ],
        [
            InlineKeyboardButton(text="📸 Instagram sahifamiz", url=config.INSTAGRAM_URL)
        ]
    ])

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin boshqaruv paneli tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="🏆 Top 20 Yetakchilar", callback_data="admin_top"),
            InlineKeyboardButton(text="🔍 Foydalanuvchi qidiruvi", callback_data="admin_search"),
        ],
        [
            InlineKeyboardButton(text="🏁 Tanlovni yakunlash (Top 3)", callback_data="admin_end_contest"),
            InlineKeyboardButton(text="🚀 Yangi 7 kunlik tanlov", callback_data="admin_new_contest"),
        ],
        [
            InlineKeyboardButton(text="❌ Panelni yopish", callback_data="admin_close")
        ]
    ])

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Xabar tarqatishni tasdiqlash tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Ha, barchaga yuborilsin", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel"),
        ]
    ])
