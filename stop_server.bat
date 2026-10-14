@echo off
chcp 65001 > nul
echo ==============================================================================
echo   🛑 A.GRID Oracle & Tunnel 서비스 안전 종료 중...
echo ==============================================================================
echo.
taskkill /F /IM cloudflared.exe > nul 2>&1
echo [OK] Cloudflare Tunnel 종료 완료.

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a > nul 2>&1
)
echo [OK] Uvicorn FastAPI Server (Port 8000) 종료 완료.

echo.
echo ==============================================================================
echo  ✅ 모든 서비스 프로세스가 정상 종료되었습니다.
echo ==============================================================================
pause
