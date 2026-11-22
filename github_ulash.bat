@echo off
chcp 65001 > nul
title UniConnect - GitHub va 24/7 Serverga Yuklash
cd /d "C:\Users\delux\.gemini\antigravity\scratch\uniconnect"
cls

echo ========================================================
echo     UniConnect Botini 24/7 Serverga Yuklash (GitHub)
echo ========================================================
echo.
echo Hozir GitHub hisobingizga ulanish oynasi ochiladi.
echo Agar GitHub akkauntingiz bo'lsa kirasiz, bo'lmasa 
echo 1 daqiqada bepul ro'yxatdan o'tasiz.
echo.
echo Davom etish uchun ixtiyoriy tugmani bosing...
pause > nul
echo.

"C:\Program Files\GitHub CLI\gh.exe" auth login --web -p https

echo.
echo ========================================================
echo Loyihangiz GitHub profilingizga yuklanmoqda...
echo ========================================================
"C:\Program Files\Git\cmd\git.exe" branch -M main
"C:\Program Files\GitHub CLI\gh.exe" repo create uniconnect-bot --public --source=. --remote=origin --push

echo.
echo ========================================================
echo  MUBORAK! Botingiz kodi GitHub ga muvaffaqiyatli yuklandi!
echo ========================================================
echo.
echo Endi Render.com saytida bitta bosish bilan botni yoqamiz!
echo.
pause
