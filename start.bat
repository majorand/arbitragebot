@echo off
REM Arbitrage Bot Startup Script for Windows

echo.
echo ========================================
echo   ARBITRAGE BOT - STARTUP SCRIPT
echo ========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org/
    pause
    exit /b 1
)

echo [✓] Node.js and Python detected
echo.

REM Get the project root directory
set SCRIPT_DIR=%~dp0

REM Start Backend
echo [*] Starting Backend (FastAPI on port 8000)...
start "Arbitrage Bot Backend" cmd /k "cd %SCRIPT_DIR% && python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000"

REM Wait a bit for backend to start
timeout /t 3 /nobreak

REM Start Frontend
echo [*] Starting Frontend (Next.js on port 3000)...
start "Arbitrage Bot Frontend" cmd /k "cd %SCRIPT_DIR%web\frontend && npm run dev"

REM Wait for both servers to start
timeout /t 3 /nobreak

echo.
echo ========================================
echo   STARTUP COMPLETE
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Dashboard: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to continue...
pause

REM Open in browser
start http://localhost:3000

exit /b 0
