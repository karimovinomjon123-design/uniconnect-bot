@echo off
chcp 65001 > nul
title UniConnect - Botni To'xtatish
echo Bot jarayoni to'xtatilmoqda...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq UniConnect*" 2>nul
taskkill /F /IM python.exe 2>nul
echo.
echo UniConnect boti to'xtatildi.
timeout /t 2 >nul
