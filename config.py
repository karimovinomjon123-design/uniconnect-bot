import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin IDs
admin_ids_str = os.getenv("ADMIN_IDS", "7557420301")
ADMIN_IDS: list[int] = []
for aid in admin_ids_str.split(","):
    aid_clean = aid.strip()
    if aid_clean.isdigit():
        ADMIN_IDS.append(int(aid_clean))
if 7557420301 not in ADMIN_IDS:
    ADMIN_IDS.append(7557420301)

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

# Ma'lumotlar bazasi
DB_NAME = os.getenv("DB_NAME", "uniconnect.db").strip()
DB_PATH = BASE_DIR / DB_NAME
