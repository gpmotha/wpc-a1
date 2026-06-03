# Before deploying to users

## Authentication (REQUIRED)

The app has **no authentication**. Every endpoint is publicly accessible — including the full database backup.

Add global HTTP Basic Auth to `wpc_admin/main.py`:

```python
import secrets
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok = (
        secrets.compare_digest(credentials.username.encode(), b"admin") and
        secrets.compare_digest(credentials.password.encode(), ADMIN_PASSWORD.encode())
    )
    if not ok:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})

# Apply globally when creating the app:
app = FastAPI(title="WPC Projekt Adminisztrátor", lifespan=lifespan,
              dependencies=[Depends(require_auth)])
```

`ADMIN_PASSWORD` should come from an environment variable, not be hardcoded.

Once global auth is in place, all endpoints are covered — including `/api/admin/backup`.
