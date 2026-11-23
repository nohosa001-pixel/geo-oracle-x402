# ========================================================
#   geo-oracle-x402 Google Cloud Run PowerShell Script
#   Region: asia-northeast3 (Seoul)
# ========================================================

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 1. Check gcloud CLI
$gcloudBin = "C:\Users\nohos\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin"
if ((Test-Path $gcloudBin) -and ($env:Path -notlike "*$gcloudBin*")) {
    $env:Path = "$gcloudBin;$env:Path"
}
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] gcloud CLI is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# 2. Load .env if present
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $k = $parts[0].Trim()
            $v = $parts[1].Trim().Trim('"').Trim("'")
            if (-not [string]::IsNullOrEmpty($k)) {
                [System.Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
}

$PROJECT_ID = (gcloud config get-value project 2>$null).Trim()
if ([string]::IsNullOrEmpty($PROJECT_ID)) {
    $PROJECT_ID = "my-nohosa-87175"
    gcloud config set project $PROJECT_ID
}

Write-Host "Deploying geo-oracle-x402 to Cloud Run ($PROJECT_ID / asia-northeast3)..." -ForegroundColor Cyan

$EVM_WALLET = if ($env:ORACLE_RECIPIENT_WALLET) { $env:ORACLE_RECIPIENT_WALLET } else { "0xEbA2821B8E37eb5a231c074345c991Cb1F139920" }
$SOL_VAULT = if ($env:SOLANA_ORACLE_VAULT) { $env:SOLANA_ORACLE_VAULT } else { "G7doJyFj1tw2mTpApCoyeCPqA3QzyuuKwKNAZvzLErsT" }

gcloud run deploy geo-oracle-x402 `
    --source . `
    --region asia-northeast3 `
    --platform managed `
    --allow-unauthenticated `
    --port 8080 `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars="ENVIRONMENT=production,ORACLE_RECIPIENT_WALLET=$EVM_WALLET,SOLANA_ORACLE_VAULT=$SOL_VAULT" `
    --project $PROJECT_ID `
    --quiet

if ($LASTEXITCODE -eq 0) {
    $url = (gcloud run services describe geo-oracle-x402 --region asia-northeast3 --format="value(status.url)" --project $PROJECT_ID).Trim()
    Write-Host "[SUCCESS] geo-oracle-x402 deployed: $url" -ForegroundColor Green
} else {
    Write-Host "[ERROR] geo-oracle-x402 deployment failed." -ForegroundColor Red
    exit 1
}
