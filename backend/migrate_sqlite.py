import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "agrisync.db"
con = sqlite3.connect(str(db_path))
cur = con.cursor()

def add_col_if_missing(table, col_def, col_name):
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    if col_name not in cols:
        print(f"Adding {col_name} to {table}")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")

add_col_if_missing("crops", "category VARCHAR(50) DEFAULT 'other' NOT NULL", "category")
add_col_if_missing("crop_machine_map", "window_days INTEGER DEFAULT 5 NOT NULL", "window_days")
add_col_if_missing("crop_machine_map", "source TEXT DEFAULT 'SAMPLE - verify with ICAR / state agriculture dept' NOT NULL", "source")
add_col_if_missing("booking_groups", "name VARCHAR(150)", "name")
add_col_if_missing("booking_groups", "description VARCHAR(500)", "description")
add_col_if_missing("booking_groups", "crop_focus VARCHAR(100)", "crop_focus")
add_col_if_missing("booking_groups", "radius_km FLOAT DEFAULT 10 NOT NULL", "radius_km")

con.commit()
con.close()
print("Migration check complete.")
