@echo off
title BitHuB Production Server

echo ==========================================
echo Starting BitHuB Production Services...
echo ==========================================

:: Start the Backend in a new window
echo Starting Node.js Backend on port 3001...
start "BitHuB Backend" cmd /c "cd Backend && npm start"

:: Wait a few seconds for the backend to initialize
timeout /t 3 /nobreak >nul

:: Start the Frontend in a new window
echo Starting React Frontend on port 3000...
start "BitHuB Frontend" cmd /c "cd \"Front-End New\" && npm run dev"

:: Wait a few seconds for the frontend to initialize
timeout /t 5 /nobreak >nul

:: Start Ngrok in the current window
echo.
echo Starting Ngrok Tunnel on port 3000...
echo ==========================================
npx ngrok http --domain=unpicked-mignon-unlawyerlike.ngrok-free.dev 3000
