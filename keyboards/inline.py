import urllib.parse
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Majburiy kanallar va guruhlar uchun inline tugmalar"""
    buttons = []
    for chat_target, chat_title, chat_url in config.REQUIRED_CHATS:
        buttons.append([InlineKeyboardButton(text=chat_title, url=chat_url)])

    buttons.append([InlineKeyboardButton(text="✅ A'zolikni tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_referral_share_keyboard(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    """Taklif havolasini do'stlarga yuborish uchun inline tugmalar"""
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_caption = (
        "👋 Salom! O'zbekiston talabalari uchun katta tanlov e'lon qilindi: "
        f"{config.COMPETITION_NAME}!\n\n"
        "🎁 G'oliblar uchun qimmatbaho sovg'alar:\n"
        f"• 1-o'rin: {config.PRIZE_1}\n"
        f"• 2-o'rin: {config.PRIZE_2}\n"
        f"• 3-o'rin: {config.PRIZE_3}\n\n"
        "Qo'shiling va birgalikda g'olib bo'lamiz 👇"
    )

    encoded_url = urllib.parse.quote(ref_link, safe="")
    encoded_text = urllib.parse.quote(share_caption, safe="")
    share_url = f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Do'stlarga va guruhlarga yuborish", url=share_url)],
        [InlineKeyboardButton(text="🔄 Statistikani yangilash", callback_data="refresh_stats")]
    ])

def get_leaderboard_keyboard(page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Reyting oynasidagi navigatsiya va yangilash tugmalari"""
    buttons = []

    # Sahifalash (Pagination)
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"leaderboard_page_{page-1}"))
        nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="ignore"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"leaderboard_page_{page+1}"))
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🔗 Taklif havolamni olish", callback_data="open_referral"),
        InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_leaderboard")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_contact_keyboard() -> InlineKeyboardMarkup:
    """Bog'lanish bo'limi uchun tugmalar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Bosh Administrator (@IKN150)", url=config.SUPPORT_ADMIN_URL),
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
    """Administrator paneli asosiy tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="🏆 Top 20 Ro'yxat", callback_data="admin_top"),
            InlineKeyboardButton(text="🔍 Foydalanuvchi qidirish", callback_data="admin_search"),
        ],
        [
            InlineKeyboardButton(text="📥 CSV Eksport", callback_data="admin_export_csv"),
            InlineKeyboardButton(text="⚠️ Shubhali faollik", callback_data="admin_suspicious"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Tanlovni boshqarish", callback_data="admin_contest_menu"),
            InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close")
        ]
    ])

def get_admin_contest_menu_keyboard(current_status: str) -> InlineKeyboardMarkup:
    """Tanlovni boshqarish bo'yicha maxsus tugmalar"""
    buttons = []
    if current_status == "upcoming":
        buttons.append([InlineKeyboardButton(text="▶️ Tanlovni muddatidan oldin boshlash", callback_data="ask_start_contest")])
    elif current_status == "running":
        buttons.append([InlineKeyboardButton(text="🏁 Tanlovni yakunlash va g'oliblarni aniqlash", callback_data="ask_end_contest")])

    buttons.append([InlineKeyboardButton(text="🔄 Yangi 7 kunlik mavsum yaratish", callback_data="ask_new_season")])
    buttons.append([InlineKeyboardButton(text="⬅️ Admin panelga qaytish", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Tasdiqlash so'rovi tugmalari (xatoliklardan himoya)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, tasdiqlayman", callback_data=f"confirm_{action}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action"),
        ]
    ])

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Ha, barchaga yuborilsin", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel"),
        ]
    ])
