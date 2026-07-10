@echo off
echo ========================================
echo IDBI Wealth Engine - Full Stack Startup
echo ========================================
echo.
echo Starting Backend and Frontend servers...
echo.

REM Start backend in a new window
start "IDBI Backend API" cmd /k "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment for backend to start
timeout /t 5 /nobreak > nul

REM Start frontend in a new window
start "IDBI Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Both servers are starting...
echo.
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo.
echo Close this window or the server windows to stop.
echo ========================================
