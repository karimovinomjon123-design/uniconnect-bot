# 🌟 UniConnect Telegram Bot

UniConnect — O'zbekiston oliy o'quv yurtlari talabalarini birlashtiruvchi, do'stona networking, referral tizimi, yetakchilar reytingi va qimmatbaho sovg'alar dasturini o'z ichiga olgan zamonaviy Telegram boti.

---

## 🚀 Texnologiyalar
- **Til:** Python 3.12
- **Telegram Framework:** Aiogram 3.33 (Asinxron)
- **Ma'lumotlar bazasi:** SQLite + aiosqlite (Tezkor va yengil)
- **Xavfsizlik:** python-dotenv (Maxfiy kalitlar .env orqali boshqariladi)

---

## 📂 Loyiha tuzilishi

```
uniconnect/
├── database/
│   ├── __init__.py
│   └── db.py            # SQLite ma'lumotlar bazasi va SQL so'rovlari
├── handlers/
│   ├── __init__.py
│   ├── start.py         # /start komandasi, ro'yxatdan o'tish va referral tahlili
│   ├── subscription.py  # Majburiy kanal a'zoligini tekshirish va tasdiqlash
│   ├── referral.py      # Shaxsiy havola, do'stlarga bitta bosishda ulashish
│   ├── leaderboard.py   # Eng faol talabalar reytingi (Top 10)
│   ├── rewards.py       # Sovg'alar bosqichlari va ularni qabul qilish
│   ├── profile.py       # Shaxsiy profil va natijalar
│   ├── info.py          # Loyiha haqida ma'lumot va aloqa
│   └── admin.py         # Admin panel (statistika, xabar tarqatish, qidiruv)
├── keyboards/
│   ├── reply.py         # Asosiy menyu tugmalari
│   └── inline.py        # Inline tugmalar (a'zolik, ulashish, sovg'alar)
├── utils/
│   └── helpers.py       # Kanal tekshiruvi va matn formatlash
├── .env                 # Maxfiy sozlamalar (BOT_TOKEN, ADMIN_IDS va hk.)
├── .env.example         # Sozlamalar namunasi
├── config.py            # Konfiguratsiya yuklovchi modul
├── main.py              # Botni ishga tushiruvchi asosiy fayl
├── requirements.txt     # Kerakli Python kutubxonalari
├── test_bot.py          # Bot funksiyalarini avtomatlashtirilgan testlari
├── run.bat              # Windows uchun bir bosishda ishga tushirish fayli
└── README.md            # Loyiha qo'llanmasi
```

---

## ⚙️ Sozlash va Ishga tushirish (Oddiy qo'llanma)

### 1-qadam: Bot Tokenini kiritish
1. Loyiha papkasidagi `.env` faylini matn muharriri (Notepad yoki VS Code) orqali oching.
2. `BOT_TOKEN=YOUR_BOT_TOKEN_HERE` qatoridagi `YOUR_BOT_TOKEN_HERE` o'rniga `@BotFather`dan olgan bot tokeningizni qo'ying.
3. `ADMIN_IDS=123456789` qatoriga o'zingizning Telegram ID raqamingizni kiriting (o'z ID raqamingizni bilish uchun Telegramda `@userinfobot` ga `/start` yuborishingiz mumkin).

### 2-qadam: Botni Kanalga Administrator qilish
Bot foydalanuvchilar rasmiy kanalingizga a'zo bo'lganini avtomatik tekshirishi uchun:
1. `@uniconnectuz_official` kanaliga kiring.
2. Kanal sozlamalaridan **Administrators (Administratorlar)** bo'limiga o'ting.
3. Botni administrator sifatida qo'shing (hech bo'lmaganda a'zolarni ko'rish huquqi bo'lishi kifoya).

### 3-qadam: Botni Ishga tushirish
- **Windows'da:** Shunchaki `run.bat` fayli ustiga 2 marta bosing!
- **Terminal orqali:**
  ```powershell
  python main.py
  ```

---

## 🏆 Asosiy Imkoniyatlar

1. **Avtomatlashtirilgan Referral tizimi:**
   - Har bir foydalanuvchiga shaxsiy havola beriladi: `https://t.me/bot_username?start=ref_USERID`
   - «Do'stlarga yuborish» tugmasi orqali bitta bosishda Telegramdagi guruhlar va do'stlarga chiroyli taklifnoma yuborish mumkin.
   - O'zini o'zi taklif qilishdan va takroriy hisoblashdan himoyalangan.
   - Do'sti faqat kanalga a'zo bo'lib botni tasdiqlaganida taklifchiga +1 ball hisoblanadi (soxta takliflardan himoya).

2. **Yetakchilar Reytingi (Leaderboard):**
   - Top 10 talaba reytingi avtomatik shakllanadi (🥇, 🥈, 🥉).
   - Har bir foydalanuvchi o'zining jami takliflari va nechanchi o'rinda ekanini ko'rib turadi.

3. **Rag'batlantirish va Sovg'alar:**
   - 5 ta do'st: Maxsus materiallar va qo'llanmalar to'plami (PDF).
   - 15 ta do'st: UniConnect VIP yopiq talabalar guruhiga kirish.
   - 30 ta do'st: UniConnect brendli esdalik sovg'alari (Merch).
   - 50 ta do'st: Yoshlar yetakchisi sertifikati va homiylar sovg'asi.
   - Sovg'ani bir marta olgandan so'ng qayta olmaslik kafolatlangan.

4. **Kengaytirilgan Admin Panel:**
   - Faqat administratorlar `/admin` komandasini ko'radi.
   - Real vaqt rejimidagi statistika (jami a'zolar, tasdiqlanganlar, bugungi ro'yxatdan o'tganlar).
   - Barcha foydalanuvchilarga xabar tarqatish (Broadcast) funksiyasi.
   - Foydalanuvchilarni ID yoki @username bo'yicha bazadan qidirish.
