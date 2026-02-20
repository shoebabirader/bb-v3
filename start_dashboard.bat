@echo off
REM Trading Bot Dashboard Launcher
REM This script starts both the trading bot and Streamlit dashboard

echo ========================================
echo Trading Bot Dashboard Launcher
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "main.py" (
    echo ERROR: main.py not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

if not exist "streamlit_app.py" (
    echo ERROR: streamlit_app.py not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM Check if config exists
if not exist "config\config.json" (
    echo WARNING: config\config.json not found
    echo Please ensure you have configured the bot before starting
    echo.
    set /p continue="Continue anyway? (y/n): "
    if /i not "%continue%"=="y" (
        echo Exiting...
        pause
        exit /b 0
    )
)

REM Check if requirements are installed
echo Checking dependencies...
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Streamlit is not installed
    echo Installing UI dependencies...
    pip install -r requirements_ui.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting Trading Bot...
start "Trading Bot" cmd /k "python main.py"

REM Wait a moment for bot to initialize
timeout /t 3 /nobreak >nul

echo Starting Streamlit Dashboard...
start "Streamlit Dashboard" cmd /k "streamlit run streamlit_app.py"

echo.
echo ========================================
echo Both services are starting...
echo.
echo Trading Bot: Running in separate window
echo Dashboard: http://localhost:8501
echo.
echo Close the command windows to stop the services
echo ========================================
echo.

REM Wait a bit more and try to open browser
timeout /t 5 /nobreak >nul
start http://localhost:8501

echo Dashboard should open in your browser shortly
echo.
pause
