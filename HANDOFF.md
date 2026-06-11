# WPC A1 — Handoff Document

**Date:** 2026-06-10  
**Author:** Gyorgy Nagy  

---

## App Overview

Internal admin tool for WPC project management. Server-side rendered — no separate frontend build step.

| Layer | Technology |
|---|---|
| Backend | Python 3.x, FastAPI |
| Templates | Jinja2 (server-side HTML) |
| Database | SQLite (`wpc_admin/wpc.db`) |
| Server | uvicorn |
| ORM | SQLModel |
| Extras | openpyxl (Excel), geocoding |

### Pages / Views

| Route | Purpose |
|---|---|
| `/` | Projects table |
| `/calendar` | Calendar view |
| `/map` | Map view |
| `/csapatok` | Teams |
| `/finance` | Finance |
| `/settings` | Settings |
| `/ajanlatok` | Offers |
| `/garancia` | Warranty |

---

## How to Run Locally

```bat
A1.bat
```

This opens `http://localhost:8000` in the browser and starts:

```
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Working directory: `wpc_admin/`. The SQLite database file is at `wpc_admin/wpc.db`.

---

## Current State & Known Issues

- **No authentication** — every endpoint is publicly accessible. This is flagged in the codebase TODO. Must be resolved before production deployment.
- The `/api/admin/backup` endpoint exposes a full database download with no protection.
- `--reload` flag is active — fine for development, remove for production.

---

## Sharing with Client (Pre-deployment)

For UI/UX validation sessions without a full deployment:

### ngrok (recommended for short sessions)
```powershell
winget install ngrok
ngrok http 8000
```
Provides a temporary public URL (e.g. `https://abc123.ngrok-free.app`). Valid while your machine runs. Free tier.

### Cloudflare Tunnel (better for multi-day access)
```powershell
winget install Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8000
```
More stable than ngrok, free, no session limits.

### Screen share
Zero setup — share your browser over Zoom/Teams. Client can't explore independently but works for guided reviews.

> **Note:** Since there is no auth, keep tunnel sessions short and shut down the tunnel when not actively reviewing.

---

## Final Deployment Recommendation

**Hetzner CX22** (~€4/month)

- 2 vCPU / 4 GB RAM — more than enough for 6 users (2 operational + 4 team leads, mostly ad-hoc, non-simultaneous)
- SQLite on a real persistent disk — no migration needed
- German datacenter — GDPR-compliant, low latency from Hungary
- Run uvicorn behind nginx; free HTTPS via Let's Encrypt

### Why not Vercel?
Vercel's filesystem is ephemeral and read-only — SQLite writes fail. It's also designed for serverless/frontend, not persistent FastAPI servers.

### Why not Render/Railway?
Valid options (~$5/month), but managed platforms add vendor complexity. For a long-lived internal tool with a known small user base, owning a VPS is simpler and cheaper over time.

---

## Pre-deployment Checklist

- [ ] Add HTTP Basic Auth globally (already flagged in TODO)
- [ ] Move any hardcoded secrets/config to environment variables
- [ ] Switch uvicorn to production mode (remove `--reload`, add `--workers 2`)
- [ ] Put nginx in front (handles HTTPS, static files)
- [ ] Test with a copy of real production data before go-live
- [ ] Set up automated SQLite backup (e.g. daily cron copying `wpc.db` to object storage)

---

## Key Files

| File | Purpose |
|---|---|
| `wpc_admin/main.py` | FastAPI app, all routes |
| `wpc_admin/models.py` | SQLModel data models |
| `wpc_admin/database.py` | DB engine, session factory |
| `wpc_admin/templates/` | Jinja2 HTML templates |
| `wpc_admin/wpc.db` | SQLite database |
| `A1.bat` | Local dev launcher |
