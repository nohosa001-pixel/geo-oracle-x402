# ==============================================================================
#   A.GRID Universal Physical AI Oracle & Logistics Escrow Suite
#   PowerShell Safe Shutdown Script
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  [A.GRID] Stopping Oracle and Tunnel Services..." -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Stop Cloudflare Tunnel
Stop-Process -Name "cloudflared" -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Cloudflare Tunnel stopped." -ForegroundColor Green

# 2. Stop Port 8000 process
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000) {
    Stop-Process -Id $port8000.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Uvicorn FastAPI Server (Port 8000) stopped." -ForegroundColor Green
} else {
    Write-Host "[OK] Port 8000 was not in use." -ForegroundColor Gray
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "  [SUCCESS] All Oracle services have been terminated." -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
