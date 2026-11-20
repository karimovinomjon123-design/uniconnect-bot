@echo off
chcp 65001 > nul
title UniConnect Telegram Bot

echo ========================================================
echo           UniConnect Telegram Bot (Faol Rejim)
echo ========================================================
echo.

set "PYTHON_CMD=C:\Users\delux\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PYTHON_CMD%" (
    set "PYTHON_CMD=python"
)

echo Bot ishga tushmoqda...
"%PYTHON_CMD%" main.py

echo.
echo Bot to'xtadi. Chiqish uchun ixtiyoriy tugmani bosing...
pause > nul
