"""
Batch geocoder CLI — resolves lat/lng for all Project records that have an
address but no coordinates. Rate-limited to 1 request/second (Nominatim ToS).

Usage (run from wpc_admin/):
    python geocoder.py           # geocode all missing
    python geocoder.py --retry   # also retry previously failed (geocode_ok=-1)
"""
import argparse
import json
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "wpc.db"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "WPC-Admin/1.0 (geocoder; contact: admin@example.com)"


def build_query(row: dict) -> dict | None:
    """Return Nominatim query params for a project row, or None if no address."""
    if row["iranyitoszam"] and row["varos"] and row["utca"] and row["hazszam"]:
        return {
            "street": f"{row['hazszam']} {row['utca']}",
            "city": row["varos"],
            "postalcode": row["iranyitoszam"],
            "country": "Hungary",
            "format": "json",
            "limit": "1",
        }
    if row["address"]:
        return {
            "q": f"{row['address']}, Hungary",
            "format": "json",
            "limit": "1",
        }
    return None


def geocode_one(params: dict) -> tuple[float, float] | None:
    """Call Nominatim; return (lat, lng) or None on failure."""
    url = NOMINATIM_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None


def run(retry_failed: bool = False) -> None:
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Start the app first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if retry_failed:
        cur.execute(
            "SELECT id, client_name, address, iranyitoszam, varos, utca, hazszam "
            "FROM project WHERE lat IS NULL OR geocode_ok = -1"
        )
    else:
        cur.execute(
            "SELECT id, client_name, address, iranyitoszam, varos, utca, hazszam "
            "FROM project WHERE lat IS NULL"
        )

    rows = cur.fetchall()
    total = len(rows)

    if total == 0:
        print("Nincs geocódolandó cím.")
        return

    errors = []
    for idx, row in enumerate(rows, 1):
        row = dict(row)
        params = build_query(row)
        now = datetime.now(timezone.utc).isoformat()

        if params is None:
            cur.execute(
                "UPDATE project SET geocode_ok=-1, geocode_at=? WHERE id=?",
                (now, row["id"]),
            )
            conn.commit()
            errors.append(f"[id={row['id']}] {row['client_name']} — nincs cím")
            print(f"  {idx}/{total} — nincs cím: {row['client_name']}")
            continue

        try:
            result = geocode_one(params)
        except Exception as exc:
            result = None
            errors.append(f"[id={row['id']}] {row['client_name']} — {exc}")

        if result:
            lat, lng = result
            cur.execute(
                "UPDATE project SET lat=?, lng=?, geocode_ok=1, geocode_at=? WHERE id=?",
                (lat, lng, now, row["id"]),
            )
            print(f"  {idx}/{total} OK  {row['client_name']}  → {lat:.4f}, {lng:.4f}")
        else:
            addr_str = params.get("q") or f"{params.get('street')}, {params.get('city')}"
            cur.execute(
                "UPDATE project SET geocode_ok=-1, geocode_at=? WHERE id=?",
                (now, row["id"]),
            )
            errors.append(f"[id={row['id']}] {row['client_name']} — nem találtam: {addr_str}")
            print(f"  {idx}/{total} FAIL {row['client_name']}  — {addr_str}")

        conn.commit()

        if idx < total:
            time.sleep(1)

    conn.close()
    print(f"\n{total - len(errors)} / {total} cím geocódolva.")
    if errors:
        print("\nHibák:")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WPC batch geocoder")
    parser.add_argument("--retry", action="store_true", help="retry previously failed records")
    args = parser.parse_args()
    run(retry_failed=args.retry)
