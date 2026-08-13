# Deployment Guide — Document Processing & Invoicing (Railway)

This guide covers deploying **only this project** (`project-3-document-processing/`) from the monorepo to Railway. Railway is the primary deployment target for this project; see the repo root `README.md` for the general platform policy.

---

## Prerequisites

- A [Railway](https://railway.app) account
- This repo pushed to GitHub (Railway deploys from a connected GitHub repo)
- Railway CLI installed locally (optional, for manual deploys): `npm i -g @railway/cli`

---

## 1. Create the Project

1. In the Railway dashboard, click **New Project → Deploy from GitHub repo**.
2. Select the `ai-automation-portfolio` repository.
3. Because this is a monorepo, set the **Root Directory** to:
   ```
   project-3-document-processing
   ```
   This is required so Railway only builds this project's `Dockerfile` and ignores the other projects in the repo.

Railway will detect `railway.toml` in this directory and use it automatically:

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python -m src.api"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

---

## 2. Database / Storage

This service does **not** need a Railway-managed database. The registry is **SQLite**, persisted to a file inside the container (`REGISTRY_DB_PATH`, default `data/registry.db`). Generated reports land in `OUTPUT_DIR` (default `data/output/`). The 10 synthetic sample documents (`data/incoming/`) ship baked into the image.

> Note: Railway's filesystem is ephemeral across deploys (a fresh deploy starts from a clean image), so the registry resets on every redeploy — re-run `POST /process` afterward. For a persistent registry and output history across restarts, attach a [Railway Volume](https://docs.railway.com/reference/volumes) mounted at the parent of `REGISTRY_DB_PATH` / `OUTPUT_DIR`; this is optional for the demo since re-processing the 10-document sample set is fast and idempotent (upsert by id).

---

## 3. Environment Variables

On the app service, set the following variables under **Variables**:

| Variable                        | Value                                              | Notes                                              |
|-----------------------------------|------------------------------------------------------|-----------------------------------------------------|
| `EXTRACTION_BACKEND`              | `mock`                                              | `RegexDocumentExtractor` — deterministic, no API key. `claude` is documented but intentionally unimplemented (raises `NotImplementedError`) so the demo never incurs API cost |
| `CLAUDE_MODEL`                    | `claude-opus-4-8`                                  | Only relevant if `EXTRACTION_BACKEND=claude` is wired up |
| `N8N_WEBHOOK_URL`                 | `http://<your-n8n-host>:5678/webhook/document-processing` | Only needed if triggering from a live n8n instance |
| `LOG_LEVEL`                       | `INFO`                                              |                                                     |
| `INCOMING_DIR`                    | `data/incoming`                                     | Ships baked into the image                         |
| `OUTPUT_DIR`                      | `data/output`                                       |                                                     |
| `REGISTRY_DB_PATH`                | `data/registry.db`                                  | Local to the container unless a Volume is attached |
| `REPORT_FORMAT`                   | `json`                                              | Or `pdf` (via `reportlab`)                          |
| `MIN_CLASSIFICATION_CONFIDENCE`   | `0.5`                                               |                                                     |
| `PORT`                            | `8002`                                              | Railway sets this automatically — do not override unless required |

These mirror `.env.example` in this folder. Do not commit a real `.env` file — Railway variables replace it in production.

---

## 4. Deploy

- **Automatic:** any push to `main` that touches `project-3-document-processing/**` triggers a new Railway build (given the Root Directory is set correctly).
- **Manual (CLI):**
  ```bash
  cd project-3-document-processing
  railway login
  railway link          # select the project created in step 1
  railway up
  ```

Railway builds the image from `Dockerfile`, which installs dependencies, copies the app (including the sample documents in `data/incoming/`), creates `logs/`, `data/output/`, and `data/incoming/`, and starts the Flask API on port 8002 via `python -m src.api`.

---

## 5. Verify the Deployment

Once the deploy finishes, Railway assigns a public domain (enable it under **Settings → Networking → Generate Domain** if not already public).

**Health check:**

```bash
curl https://<your-railway-domain>/health
# Expected: {"status": "ok", "service": "document-processing-pipeline"}
```

Railway also polls this same endpoint (`healthcheckPath = "/health"` in `railway.toml`) after every deploy — if it doesn't return `200` within `healthcheckTimeout` (300s), the deploy is marked unhealthy and rolled back.

**Process the sample batch:**

```bash
curl -X POST https://<your-railway-domain>/process \
  -H "Content-Type: application/json" \
  -d '{}'
```

With no `sources` in the body, this processes every file in `data/incoming/` (the 10 synthetic documents). Expected response: `{"status": "success", "result": {...}}` with per-document status totals — the reference run on this dataset produces 8 `reported`, 2 `needs_review`, 0 `failed`.

**Query the registry:**

```bash
curl "https://<your-railway-domain>/documents?status=needs_review"
curl "https://<your-railway-domain>/documents/<doc_id>"
```

---

## Troubleshooting

**Build fails on `pip install`**
Check the build logs for a specific package failure. `pypdf` and `reportlab` are pure-Python; `gcc` is already installed in the `Dockerfile` for any compiled transitive dependency — if you modified the Dockerfile, confirm that layer is still present.

**Healthcheck fails / deploy marked unhealthy**
- Confirm `PORT` is not hardcoded to something other than what Railway expects — the app reads `PORT` from the environment (`src/api.py`) and defaults to 8002, which matches `EXPOSE 8002` in the Dockerfile.
- Check that the Root Directory is set to `project-3-document-processing` — if Railway is building from the repo root instead, it will use the wrong (or no) Dockerfile.

**`POST /process` returns a 500 error**
- Check the Railway logs (`railway logs` or the dashboard **Deployments → Logs** tab) for the loguru-formatted error. Note the pipeline itself catches per-document failures internally (`status=FAILED`, `error_message` set on the document) — a 500 here means the batch call itself failed (e.g., bad request body), not an individual document.

**`GET /documents` returns an empty list**
- `POST /process` hasn't been run yet on this deploy, or the registry was reset by a redeploy (no Volume attached — see step 2). Re-run `/process`.

**Cold starts / first request is slow**
Railway containers stay warm as long as the service has traffic; there's no Render-style cold start on Railway's paid plans. If you see a slow first response, check whether the service recently restarted (crash loop, redeploy) in the **Deployments** tab.
