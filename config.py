import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Administratorlar Telegram ID raqamlari
admin_ids_str = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS: list[int] = []
if admin_ids_str:
    for aid in admin_ids_str.replace(";", ",").replace(" ", ",").split(","):
        aid_clean = aid.strip()
        if aid_clean.isdigit():
            val = int(aid_clean)
            if val not in ADMIN_IDS:
                ADMIN_IDS.append(val)

# Agar ADMIN_IDS berilmagan bo'lsa, zaxira sifatida standart adminlar
if not ADMIN_IDS:
    ADMIN_IDS = [8786525548, 7557420301]

def is_admin(user_id: int | str | None) -> bool:
    """Foydalanuvchining admin ekanligini xavfsiz va to'liq tekshirish"""
    if user_id is None:
        return False
    try:
        return int(user_id) in ADMIN_IDS
    except (ValueError, TypeError):
        return False

# Majburiy a'zo bo'lish kanali va guruhi
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@uniconnectuz_official").strip()
REQUIRED_CHANNEL_URL = os.getenv("REQUIRED_CHANNEL_URL", "https://t.me/uniconnectuz_official").strip()

REQUIRED_GROUP = os.getenv("REQUIRED_GROUP", "@uniconnect_uz").strip()
REQUIRED_GROUP_URL = os.getenv("REQUIRED_GROUP_URL", "https://t.me/uniconnect_uz").strip()

# Majburiy obunalar ro'yxati: (chat_username/id, nom, url)
REQUIRED_CHATS = [
    (REQUIRED_CHANNEL, "📢 UniConnect Rasmiy Kanal", REQUIRED_CHANNEL_URL),
    (REQUIRED_GROUP, "💬 UniConnect Talabalar Guruhi", REQUIRED_GROUP_URL)
]

# Ijtimoiy tarmoqlar
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://www.instagram.com/uniconnect_uz").strip()

# Bog'lanish ma'lumotlari
SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+998 70 320 88 00").strip()
SUPPORT_ADMIN = os.getenv("SUPPORT_ADMIN", "@IKN150").strip()
SUPPORT_ADMIN_URL = f"https://t.me/{SUPPORT_ADMIN.replace('@', '')}"

# ================= 7 DAYS REFERRAL CHALLENGE KONFIGURATSIYASI =================
COMPETITION_NAME = "UniConnect UZ — 7 DAYS REFERRAL CHALLENGE"
# Asia/Tashkent (UTC+5) vaqti bo'yicha:
# Boshlanish: 2026-yil 23-noyabr 00:00:00
# Tugash: 2026-yil 29-noyabr 23:59:59
COMPETITION_START_ISO = "2026-11-23T00:00:00+05:00"
COMPETITION_END_ISO = "2026-11-29T23:59:59+05:00"
MIN_REFERRALS_FOR_PRIZE = 20

PRIZE_1 = "3 oylik Telegram Premium"
PRIZE_2 = "50,000 UZS"
PRIZE_3 = "30,000 UZS"

# Ma'lumotlar bazasi (Dual-engine: PostgreSQL yoki SQLite)
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_NAME = os.getenv("DB_NAME", "uniconnect.db").strip()
DB_PATH = BASE_DIR / DB_NAME
