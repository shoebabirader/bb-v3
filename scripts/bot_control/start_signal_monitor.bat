@echo off
echo ========================================
echo Trading Signal Monitor
echo ========================================
echo.
echo Choose your option:
echo 1. FREE version (CallMeBot - No registration)
echo 2. Twilio version (More reliable, requires account)
echo.
set /p choice="Enter 1 or 2: "

if "%choice%"=="1" (
    echo.
    echo Starting FREE signal monitor...
    python signal_monitor_free.py
) else if "%choice%"=="2" (
    echo.
    echo Starting Twilio signal monitor...
    python signal_monitor_whatsapp.py
) else (
    echo Invalid choice!
    pause
)
