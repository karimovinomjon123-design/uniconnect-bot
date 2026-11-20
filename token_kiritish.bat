@echo off
chcp 65001 > nul
title UniConnect - Bot Tokenini Sozlash
cls

echo ========================================================
echo        UniConnect Telegram Bot - Token Sozlash
echo ========================================================
echo.
echo BotFather bergan bot tokenini kiriting:
echo (Masalan: 1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ)
echo.
set /p TOKEN="Tokenni shu yerga joylang (Ctrl+V) va Enter bosing: "

if "%TOKEN%"=="" (
    echo.
    echo Xatolik: Hech narsa kiritilmadi!
    pause
    exit /b
)

:: Python orqali .env fayliga chiroyli va xavfsiz yozish
"C:\Users\delux\AppData\Local\Programs\Python\Python312\python.exe" -c "import re; p = r'C:\Users\delux\.gemini\antigravity\scratch\uniconnect\.env'; c = open(p, 'r', encoding='utf-8').read(); c = re.sub(r'BOT_TOKEN=.*', f'BOT_TOKEN=%TOKEN%', c); open(p, 'w', encoding='utf-8').write(c)"

echo.
echo ========================================================
echo  MUBORAK! Token muvaffaqiyatli saqlandi!
echo ========================================================
echo.
echo Endi bemalol 'UniConnect Botni Ishga Tushirish' belgisini
echo bosib botni ishlatishingiz mumkin!
echo.
pause
