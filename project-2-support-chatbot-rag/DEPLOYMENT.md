# Deployment Guide — RAG Support Chatbot (Railway)

This guide covers deploying **only this project** (`project-2-support-chatbot-rag/`) from the monorepo to Railway. Railway is the primary deployment target for this project; see the repo root `README.md` for the general platform policy.

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
   project-2-support-chatbot-rag
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

Unlike Project #1, this service does **not** need a Railway-managed database. The vector store is **ChromaDB in embedded mode** — it persists to a local directory (`CHROMA_PERSIST_DIR`, default `data/chroma_store`) inside the container's filesystem. No external service to provision.

> Note: Railway's filesystem is ephemeral across deploys (a fresh deploy starts from a clean image). The knowledge base is re-ingested via `POST /ingest` after each deploy — see step 5. For a persistent index across restarts without re-ingesting, attach a [Railway Volume](https://docs.railway.com/reference/volumes) mounted at `CHROMA_PERSIST_DIR`; this is optional for the demo since re-ingestion is fast (20 docs) and idempotent.

---

## 3. Environment Variables

On the app service, set the following variables under **Variables**:

| Variable                    | Value                                      | Notes                                              |
|------------------------------|---------------------------------------------|-----------------------------------------------------|
| `CLAUDE_MODEL`                | `claude-opus-4-8`                          | No real API key required — answer generation is simulated |
| `N8N_WEBHOOK_URL`             | `http://<your-n8n-host>:5678/webhook/support-query` | Only needed if triggering from a live n8n instance |
| `LOG_LEVEL`                   | `INFO`                                     |                                                     |
| `CHROMA_PERSIST_DIR`          | `data/chroma_store`                        | Local to the container unless a Volume is attached |
| `COLLECTION_NAME`             | `acmecrm_knowledge_base`                   |                                                     |
| `KNOWLEDGE_BASE_DIR`          | `data/knowledge_base`                      | Ships baked into the image                         |
| `EMBEDDING_DIM`               | `256`                                       |                                                     |
| `CHUNK_SIZE`                  | `120`                                       | Words per chunk                                    |
| `CHUNK_OVERLAP`               | `20`                                        | Words of overlap between consecutive chunks        |
| `TOP_K`                       | `4`                                         | Chunks retrieved per query                         |
| `MIN_CONFIDENCE_THRESHOLD`    | `0.15`                                      | Below this, the agent returns a fallback answer    |
| `PORT`                        | `8001`                                      | Railway sets this automatically — do not override unless required |

These mirror `.env.example` in this folder. Do not commit a real `.env` file — Railway variables replace it in production.

---

## 4. Deploy

- **Automatic:** any push to `main` that touches `project-2-support-chatbot-rag/**` triggers a new Railway build (given the Root Directory is set correctly).
- **Manual (CLI):**
  ```bash
  cd project-2-support-chatbot-rag
  railway login
  railway link          # select the project created in step 1
  railway up
  ```

Railway builds the image from `Dockerfile`, which installs dependencies, copies the app, creates `logs/` and `data/chroma_store/`, and starts the Flask API on port 8001 via `python -m src.api`.

---

## 5. Verify the Deployment

Once the deploy finishes, Railway assigns a public domain (enable it under **Settings → Networking → Generate Domain** if not already public).

**Health check:**

```bash
curl https://<your-railway-domain>/health
# Expected: {"status": "ok", "service": "rag-support-chatbot"}
```

Railway also polls this same endpoint (`healthcheckPath = "/health"` in `railway.toml`) after every deploy — if it doesn't return `200` within `healthcheckTimeout` (300s), the deploy is marked unhealthy and rolled back.

**Build the vector store (run once per deploy, unless a Volume is attached):**

```bash
curl -X POST https://<your-railway-domain>/ingest
```

Expected response: `{"status": "success", "result": {...}}` with the number of documents and chunks indexed.

**Ask a question:**

```bash
curl -X POST https://<your-railway-domain>/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I export my contacts from AcmeCRM?"}'
```

Expected response: `{"status": "success", "result": {...}}` with the answer, cited source documents, and a confidence score.

---

## Troubleshooting

**Build fails on `pip install`**
Check the build logs for a specific package failure. `chromadb` pulls in a few compiled dependencies; the `Dockerfile` already installs `gcc` for this — if you modified the Dockerfile, confirm that layer is still present.

**Healthcheck fails / deploy marked unhealthy**
- Confirm `PORT` is not hardcoded to something other than what Railway expects — the app reads `PORT` from the environment (`src/api.py`) and defaults to 8001, which matches `EXPOSE 8001` in the Dockerfile.
- Check that the Root Directory is set to `project-2-support-chatbot-rag` — if Railway is building from the repo root instead, it will use the wrong (or no) Dockerfile.

**`POST /query` returns a 500 error**
- Check the Railway logs (`railway logs` or the dashboard **Deployments → Logs** tab) for the loguru-formatted error — every failure is logged with the specific stage (retrieval vs. answer generation).
- Most common cause: `/ingest` was never called after the deploy, so the collection is empty. Retrieval on an empty collection doesn't error — it returns no chunks, which routes the agent to its fallback escalation answer with `confidence: 0`; this is expected behavior, not a bug.

**`POST /query` always returns the fallback / escalation answer**
- Confirm `/ingest` completed successfully (check its response for the indexed chunk count).
- If a Railway Volume is *not* attached, a redeploy wipes the vector store — re-run `/ingest` after every deploy.

**Cold starts / first request is slow**
Railway containers stay warm as long as the service has traffic; there's no Render-style cold start on Railway's paid plans. If you see a slow first response, check whether the service recently restarted (crash loop, redeploy) in the **Deployments** tab.
