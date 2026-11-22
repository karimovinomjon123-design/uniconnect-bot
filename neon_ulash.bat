@echo off
chcp 65001 >nul
cls
echo ============================================================
echo   UNICONNECT UZ: NEON POSTGRESQL ULASH VA MIGRATSIYA
echo ============================================================
echo.
echo Neon.tech konsolidan nusxalangan "Connection string"ni kiriting:
echo (Masalan: postgresql://neondb_owner:parol@ep-xyz.neon.tech/neondb?sslmode=require)
echo.
set /p NEON_URL="DATABASE_URL ni kiriting: "

if "%NEON_URL%"=="" (
    echo [XATOLIK] Bo'sh qiymat kiritildi. Jarayon to'xtatildi.
    pause
    exit /b 1
)

python -c "import os; p = '.env'; lines = [l for l in open(p, encoding='utf-8') if not l.startswith('DATABASE_URL=')] if os.path.exists(p) else []; open(p, 'w', encoding='utf-8').write(''.join(lines) + f'\nDATABASE_URL={os.environ[\"NEON_URL\"].strip()}\n')"

echo.
echo [MUVAFFAQIYATLI] DATABASE_URL .env fayliga xavfsiz saqlandi!
echo.
echo Endi SQLite bazasini Neon PostgreSQL ga ko'chirish (migratsiya) boshlanmoqda...
echo.
python scripts\migrate_sqlite_to_pg.py

echo.
pause
