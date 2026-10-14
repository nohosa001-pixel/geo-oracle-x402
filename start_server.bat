@echo off
chcp 65001 > nul
echo ==============================================================================
echo   🛰️ A.GRID Universal Physical AI Oracle & Logistics Escrow Suite
echo ==============================================================================
echo.
echo [1/2] FastAPI Uvicorn 서버를 백그라운드로 기동합니다 (Port 8000)...
start "A.GRID-FastAPI-Server" /min python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak > nul

echo [2/2] Cloudflare 글로벌 보안 터널을 연결합니다...
start "A.GRID-Cloudflare-Tunnel" .\cloudflared.exe tunnel --url http://127.0.0.1:8000

echo.
echo ==============================================================================
echo  ✅ 서비스가 성공적으로 기동되었습니다!
echo  - 로컬 API 문서 : http://localhost:8000/docs
echo  - 헬스체크 확인 : http://localhost:8000/health
echo  - 터널 콘솔창에서 실시간 배정된 https://...trycloudflare.com 도메인을 확인하세요.
echo ==============================================================================
pause
