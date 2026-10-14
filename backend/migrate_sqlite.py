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
add_col_if_missing("crop_stages", "stage_description TEXT", "stage_description")
add_col_if_missing("crop_stages", "source VARCHAR(255) DEFAULT 'SAMPLE - verify with ICAR / state agriculture dept' NOT NULL", "source")

# Stage A: rich machine listing fields (008_machine_media_and_specs)
add_col_if_missing("machines", "mobilization_cost FLOAT DEFAULT 0 NOT NULL", "mobilization_cost")
add_col_if_missing("machines", "photos TEXT", "photos")           # stored as JSON string
add_col_if_missing("machines", "description TEXT", "description")
add_col_if_missing("machines", "model_year INTEGER", "model_year")
add_col_if_missing("machines", "specifications TEXT", "specifications")  # stored as JSON string

con.commit()
con.close()
print("Migration check complete.")
