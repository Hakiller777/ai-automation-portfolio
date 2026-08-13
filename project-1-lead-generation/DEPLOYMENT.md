# Deployment Guide — Lead Generation + Outreach (Railway)

This guide covers deploying **only this project** (`project-1-lead-generation/`) from the monorepo to Railway. Railway is the primary deployment target for this project; see the repo root `README.md` for the general platform policy.

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
   project-1-lead-generation
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

## 2. Add a PostgreSQL Database

1. In the same Railway project, click **New → Database → Add PostgreSQL**.
2. Railway automatically provisions a `DATABASE_URL`-style connection and exposes it as a Railway-managed variable on the Postgres service.
3. Copy the generated connection string — you'll reference it in the app service's environment variables in the next step (Railway lets you reference it directly with `${{Postgres.DATABASE_URL}}` if both services are in the same project).

---

## 3. Environment Variables

On the **app service** (not the Postgres service), set the following variables under **Variables**:

| Variable               | Value                                          | Notes                                              |
|-------------------------|------------------------------------------------|-----------------------------------------------------|
| `CLAUDE_MODEL`           | `claude-opus-4-8`                              | No real API key required — scoring/outreach are simulated |
| `DATABASE_URL`           | `${{Postgres.DATABASE_URL}}`                   | Reference to the Postgres plugin added in step 2   |
| `N8N_WEBHOOK_URL`        | `http://<your-n8n-host>:5678/webhook/leads`     | Only needed if triggering from a live n8n instance |
| `LOG_LEVEL`              | `INFO`                                         |                                                     |
| `BATCH_SIZE`             | `10`                                            |                                                     |
| `MIN_SCORE_THRESHOLD`    | `4`                                             | Leads below this are disqualified                  |
| `HOT_THRESHOLD`          | `8`                                             |                                                     |
| `WARM_THRESHOLD`         | `5`                                             |                                                     |
| `PORT`                   | `8000`                                          | Railway sets this automatically — do not override unless required |

These mirror `.env.example` in this folder. Do not commit a real `.env` file — Railway variables replace it in production.

---

## 4. Deploy

- **Automatic:** any push to `main` that touches `project-1-lead-generation/**` triggers a new Railway build (given the Root Directory is set correctly).
- **Manual (CLI):**
  ```bash
  cd project-1-lead-generation
  railway login
  railway link          # select the project created in step 1
  railway up
  ```

Railway builds the image from `Dockerfile`, which installs dependencies, copies the app, creates `logs/` and `data/output/`, and starts the Flask API on port 8000 via `python -m src.api`.

---

## 5. Verify the Deployment

Once the deploy finishes, Railway assigns a public domain (enable it under **Settings → Networking → Generate Domain** if not already public).

**Health check:**

```bash
curl https://<your-railway-domain>/health
# Expected: {"status": "ok", "service": "lead-generation-pipeline"}
```

Railway also polls this same endpoint (`healthcheckPath = "/health"` in `railway.toml`) after every deploy — if it doesn't return `200` within `healthcheckTimeout` (300s), the deploy is marked unhealthy and rolled back.

**Trigger a pipeline run:**

```bash
curl -X POST https://<your-railway-domain>/run \
  -H "Content-Type: application/json" \
  -d '{"input_file": "data/sample_leads.csv"}'
```

Expected response: `{"status": "success", "result": {...}}` with totals for enriched, scored, outreached, disqualified, and hot/warm/cold counts.

---

## Troubleshooting

**Build fails on `pip install`**
Check the build logs for a specific package failure. `psycopg2-binary` occasionally needs `libpq-dev`, which is already installed in the `Dockerfile` — if you modified the Dockerfile, confirm that layer is still present.

**Healthcheck fails / deploy marked unhealthy**
- Confirm `PORT` is not hardcoded to something other than what Railway expects — the app reads `PORT` from the environment (`src/api.py`) and defaults to 8000, which matches `EXPOSE 8000` in the Dockerfile.
- Check that the Root Directory is set to `project-1-lead-generation` — if Railway is building from the repo root instead, it will use the wrong (or no) Dockerfile.

**`POST /run` returns a 500 error**
- Check the Railway logs (`railway logs` or the dashboard **Deployments → Logs** tab) for the loguru-formatted error — every failure in the pipeline is logged with the specific stage and lead ID.
- Most common cause: `input_file` path doesn't exist in the deployed container. The sample CSV ships at `data/sample_leads.csv` relative to the app root; if you're POSTing a custom path, it must exist inside the container (mount a volume or bake the file into the image).

**Database connection errors**
- Confirm the Postgres plugin is in the same Railway project and `DATABASE_URL` is referenced correctly (`${{Postgres.DATABASE_URL}}`).
- The current pipeline doesn't require Postgres for the demo CLI/API flow (leads are read from CSV and written to CSV/JSON) — Postgres is provisioned for n8n's own persistence and future stateful features. If Postgres isn't reachable, the `/run` endpoint will still succeed; only n8n-side persistence would be affected.

**Cold starts / first request is slow**
Railway containers stay warm as long as the service has traffic; there's no Render-style cold start on Railway's paid plans. If you see a slow first response, check whether the service recently restarted (crash loop, redeploy) in the **Deployments** tab.
