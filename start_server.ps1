# ==============================================================================
#   A.GRID Universal Physical AI Oracle & Logistics Escrow Suite
#   PowerShell Launcher
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  [A.GRID] Universal Physical AI Oracle & Logistics Escrow Suite" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Starting FastAPI Uvicorn Server in background (Port 8000)..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -WindowStyle Minimized

Start-Sleep -Seconds 3

Write-Host "[2/2] Starting Cloudflare Global Secure Tunnel..." -ForegroundColor Yellow
Start-Process -FilePath ".\cloudflared.exe" -ArgumentList "tunnel --url http://127.0.0.1:8000"

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "  [SUCCESS] Services have been started!" -ForegroundColor Green
Write-Host "  - Local Swagger Docs : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Health Check       : http://localhost:8000/health" -ForegroundColor White
Write-Host "  - Solana Pay Portal  : http://localhost:8000/solana-pay" -ForegroundColor White
Write-Host "  - Public URL         : Check the Cloudflare console window for trycloudflare.com" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Green
