@echo off
echo ===================================================
echo    BitHuB Admin Dashboard Startup Script
echo ===================================================

echo [1/2] Starting Backend Server (Port 3001)...
start "BitHuB Backend" cmd /k "cd Backend && node index.js"

echo [2/2] Starting Admin Dashboard Frontend (Port 3002)...
start "BitHuB Admin Dashboard" cmd /k "cd Admin-Dashboard && npm run dev"

echo.
echo Both servers have been launched in separate windows!
echo Once they boot up, access the dashboard at: http://localhost:3002
echo.
pause
