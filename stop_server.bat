@echo off
@rem ==============================================================================
@rem   A.GRID Oracle and Tunnel Service Safe Shutdown
@rem ==============================================================================

echo ==============================================================================
echo   [A.GRID] Stopping Oracle and Tunnel Services...
echo ==============================================================================
echo.
taskkill /F /IM cloudflared.exe > nul 2>&1
echo [OK] Cloudflare Tunnel stopped.

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a > nul 2>&1
)
echo [OK] Uvicorn FastAPI Server (Port 8000) stopped.

echo.
echo ==============================================================================
echo   [SUCCESS] All Oracle services have been terminated.
echo ==============================================================================
pause
