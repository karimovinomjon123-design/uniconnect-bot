# UniConnect Telegram Bot PowerShell Launcher
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "          UniConnect Telegram Bot Launcher" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Cyan

$pythonPath = "C:\Users\delux\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = "python"
}

Write-Host "Bot ishga tushirilmoqda..." -ForegroundColor Green
& $pythonPath (Join-Path $PSScriptRoot "main.py")
