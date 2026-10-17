@echo off
@rem ==============================================================================
@rem   A.GRID Universal Physical AI Oracle and Logistics Escrow Suite
@rem ==============================================================================

echo ==============================================================================
echo   [A.GRID] Universal Physical AI Oracle and Logistics Escrow Suite
echo ==============================================================================
echo.
echo [1/2] Starting FastAPI Uvicorn Server in background (Port 8000)...
start "A.GRID-FastAPI-Server" /min python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak > nul

echo [2/2] Starting Cloudflare Global Secure Tunnel...
start "A.GRID-Cloudflare-Tunnel" cloudflared.exe tunnel --url http://127.0.0.1:8000

echo.
echo ==============================================================================
echo   [SUCCESS] Services have been started!
echo   - Local Swagger Docs : http://localhost:8000/docs
echo   - Health Check       : http://localhost:8000/health
echo   - Solana Pay Portal  : http://localhost:8000/solana-pay
echo   - Public URL         : Check the Cloudflare console window for trycloudflare.com
echo ==============================================================================
pause
