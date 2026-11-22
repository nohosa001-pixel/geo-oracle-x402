# Operations, Deployment & Monitoring Guide (`geo-oracle-x402` v3.0.0)

## 1. Cloud Run Deployment & Live Verification

### Manual Deploy (CLI)
```bash
gcloud run deploy geo-oracle-x402 \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars "CORS_ALLOW_ORIGINS=*,PREVIEW_RATE_LIMIT_PER_MIN=30"
```

### Live Smoke Test
```bash
python scripts/smoke_test_live.py --url https://<YOUR-CLOUD-RUN-URL>
```

---

## 2. CI/CD Automated Deployment (GitHub Actions)

Workflow file: `.github/workflows/deploy-cloudrun.yml`
- Triggers on **Git tags (`v*`)** or manual **Actions -> Deploy to Cloud Run -> Run workflow**.
- Runs `python -m pytest -v` first, deploys to Cloud Run only if all tests pass, and runs `scripts/smoke_test_live.py` against the deployed URL.

### Required GitHub Repository Secrets
1. `GCP_WIF_PROVIDER`: Workload Identity Federation provider resource name
2. `GCP_SERVICE_ACCOUNT`: GCP Service Account email with `roles/run.admin`, `roles/iam.serviceAccountUser`, `roles/cloudbuild.builds.editor`

---

## 3. Cloud Logging & Monitoring Alerts

`app/core/observability.py` emits single-line JSON logs parsed automatically by Google Cloud Logging.

### Recommended Log-Based Alert Filters
1. **Sub-Oracle Degraded Fallback**:
   ```text
   resource.type="cloud_run_revision"
   jsonPayload.event="suboracle_degraded_fallback"
   ```
   - Alert condition: count >= 5 within 5 minutes.
2. **Free Preview Rate-Limit Abuse**:
   ```text
   resource.type="cloud_run_revision"
   jsonPayload.event="rate_limit_exceeded"
   ```
   - Alert condition: count >= 20 within 5 minutes.
3. **API 5xx Server Errors**:
   ```text
   resource.type="cloud_run_revision"
   jsonPayload.event="http_api_request"
   jsonPayload.status_code>=500
   ```
4. **Uptime Check**:
   - Target: `HTTPS GET https://<YOUR-CLOUD-RUN-URL>/health` every 1-5 minutes (expected `HTTP 200`).

---

## 4. Scaling to Multi-Instance & Live x402 Settlement

When scaling Cloud Run above 1 instance or enabling live Facilitator settlement:

```bash
gcloud run services update geo-oracle-x402 \
  --region asia-northeast3 \
  --set-env-vars "REDIS_URL=redis://<HOST>:6379/0,X402_ENABLE_FACILITATOR=true,X402_FACILITATOR_URL=https://facilitator.x402.org/v1/verify"
```
- `REDIS_URL` automatically activates `RedisNonceStore` in `app/core/nonce_store.py` so anti-replay nonces are shared across all Cloud Run instances.
- `X402_ENABLE_FACILITATOR=true` activates external settlement verification in `app/core/x402_verifier.py`.
