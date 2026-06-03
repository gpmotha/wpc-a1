"""
One-time migration: adds geocoding and structured address columns to the
existing `project` table.  Safe to run multiple times — uses ALTER TABLE
which SQLite ignores with "duplicate column name" errors (caught below).
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "wpc.db")

NEW_COLUMNS = [
    ("iranyitoszam", "TEXT"),
    ("varos",        "TEXT"),
    ("utca",         "TEXT"),
    ("hazszam",      "TEXT"),
    ("egyeb",        "TEXT"),
    ("lat",          "REAL"),
    ("lng",          "REAL"),
    ("geocode_ok",   "INTEGER DEFAULT 0"),
    ("geocode_at",   "TEXT"),
]


def migrate() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    added = 0
    for col, col_type in NEW_COLUMNS:
        try:
            cur.execute(f"ALTER TABLE project ADD COLUMN {col} {col_type}")
            added += 1
            print(f"  + added column: {col} {col_type}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  · already exists: {col}")
            else:
                raise
    conn.commit()
    conn.close()
    print(f"\nMigration complete. {added} new column(s) added.")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Start the app first to create it.")
    else:
        migrate()
