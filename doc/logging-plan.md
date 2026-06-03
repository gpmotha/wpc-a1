# Logging Plan — WPC Admin

## Context
The app currently has no persistent logging. All output goes to uvicorn stdout and is lost on restart.
This means background task errors (geocoding) are silently swallowed and there is no audit trail.

## Goal
- Write logs to a rotating file (`logs/app.log`) so they survive restarts and can be read by tools
- Keep human-readable stdout for dev
- Capture currently-silent exception paths

---

## Step 1 — Create `wpc_admin/logging_config.py`

```python
import logging
import logging.handlers
import os


def setup_logging(log_dir: str = "logs") -> None:
    os.makedirs(log_dir, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")

    # stdout handler
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    # rotating file handler — 5 MB × 3 backups
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(sh)
    root.addHandler(fh)

    # suppress noisy SQLAlchemy engine SQL echo
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
```

---

## Step 2 — Update `wpc_admin/main.py`

At the very top (after stdlib imports, before FastAPI setup):

```python
import logging
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
```

Inside the `lifespan` context manager, after `create_tables()`:
```python
logger.info("App startup complete — tables ready")
```

In `_run_geocode_background`, replace bare `except Exception:` with:
```python
except Exception as exc:
    logger.exception("Geocode failed for project id=%s: %s", p.id, exc)
    p.geocode_ok = -1
```

In `_geocode_project_by_id`, same treatment for the except block.

In `calendar_entry_upsert`, after the try/except for bad input:
```python
logger.warning("Invalid calendar entry body: %s", exc)
```

---

## Step 3 — `.gitignore`

Add to the root `.gitignore`:
```
wpc_admin/logs/
```

---

## Verification

1. Restart: `cd wpc_admin && uvicorn main:app --reload`
2. Check `wpc_admin/logs/app.log` exists and has startup line
3. Make a few requests — INFO lines appear in the file
4. Deliberately break a geocode address — exception is captured in the log
