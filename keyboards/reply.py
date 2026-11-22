from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """UniConnect asosiy professional menyu tugmalari"""
    keyboard = [
        [
            KeyboardButton(text="🔗 Taklif havolam"),
            KeyboardButton(text="📊 Mening statistikam"),
        ],
        [
            KeyboardButton(text="🏆 Reyting"),
            KeyboardButton(text="🎁 Sovg'alar"),
        ],
        [
            KeyboardButton(text="⏳ Tanlov holati"),
            KeyboardButton(text="📜 Tanlov qoidalari"),
        ],
        [
            KeyboardButton(text="👤 Mening profilim"),
            KeyboardButton(text="ℹ️ Loyiha haqida"),
        ],
        [
            KeyboardButton(text="📞 Bog'lanish"),
        ]
    ]

    if is_admin:
        keyboard.append([KeyboardButton(text="⚙️ Admin Panel")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Bo'limni tanlang..."
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
