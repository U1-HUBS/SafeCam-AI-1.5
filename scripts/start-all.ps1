# Safecam AI - Local Development Startup Script
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Starting Safecam AI (Backend + Frontend)   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Ensure sample videos exist
if (!(Test-Path "sample_videos\sample_hallway.mp4")) {
    Write-Host "[1/3] Generating synthetic sample videos..." -ForegroundColor Yellow
    python sample_videos\generate_sample.py
}

# 2. Start Backend API in a new PowerShell window
Write-Host "[2/3] Launching Flask Backend on http://localhost:5000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..'; python backend\app.py"

# 3. Start Next.js Frontend in a new PowerShell window
Write-Host "[3/3] Launching Next.js Frontend on http://localhost:3000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\frontend'; npm run dev"

Write-Host ""
Write-Host "Safecam AI is running!" -ForegroundColor Cyan
Write-Host "- Dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "- Backend API: http://localhost:5000" -ForegroundColor White
Write-Host "=============================================" -ForegroundColor Cyan
