import sys
import asyncio
import math
import random
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from geoalchemy2.elements import WKTElement

from app.core.database import AsyncSessionLocal, Base, engine
from app.models import (
    User, FarmerProfile, Provider, Crop, CropStage, NutrientRule,
    Farm, SoilTest, FertilizerHistory, MachineType, Machine,
    CropMachineMap, BookingGroup, GroupMember, InputSeller, Notification
)

PUNE_LAT = 18.5204
PUNE_LON = 73.8567

# Sample Villages & Districts around Pune
PUNE_LOCATIONS = [
    ("Haveli", "Pune", 18.4500, 73.8000),
    ("Khed", "Pune", 18.8500, 73.9000),
    ("Shirur", "Pune", 18.8300, 74.3700),
    ("Baramati", "Pune", 18.1500, 74.5800),
    ("Junnar", "Pune", 19.2000, 73.8700),
    ("Purandar", "Pune", 18.2800, 73.9700),
    ("Maval", "Pune", 18.7500, 73.5300),
    ("Mulshi", "Pune", 18.5000, 73.5100),
    ("Daund", "Pune", 18.4600, 74.5800),
    ("Indapur", "Pune", 18.1100, 74.9000),
]


def random_offset_coords(base_lat, base_lon, radius_km=15):
    """Generate slightly randomized lat/lon around a base coordinate within radius_km."""
    radius_deg = radius_km / 111.0
    u = random.random()
    v = random.random()
    w = radius_deg * math.sqrt(u)
    t = 2 * math.pi * v
    lat_offset = w * math.cos(t)
    lon_offset = w * math.sin(t) / math.cos(math.radians(base_lat))
    return round(base_lat + lat_offset, 6), round(base_lon + lon_offset, 6)


async def seed_data():
    # Ensure tables exist for local testing
    if "sqlite" in str(engine.url):
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).resolve().parents[1] / "agrisync.db"
        if db_path.exists():
            con = sqlite3.connect(str(db_path))
            cur = con.cursor()
            def _add_col(table, col_def, col_name):
                cur.execute(f"PRAGMA table_info({table})")
                cols = [r[1] for r in cur.fetchall()]
                if col_name not in cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            try:
                _add_col("crops", "category VARCHAR(50) DEFAULT 'other' NOT NULL", "category")
                _add_col("crop_machine_map", "window_days INTEGER DEFAULT 5 NOT NULL", "window_days")
                _add_col("crop_machine_map", "source TEXT DEFAULT 'SAMPLE - verify with ICAR / state agriculture dept' NOT NULL", "source")
                _add_col("booking_groups", "name VARCHAR(150)", "name")
                _add_col("booking_groups", "description VARCHAR(500)", "description")
                _add_col("booking_groups", "crop_focus VARCHAR(100)", "crop_focus")
                _add_col("booking_groups", "radius_km FLOAT DEFAULT 10 NOT NULL", "radius_km")
                _add_col("farms", "irrigation_type_note TEXT", "irrigation_type_note")
                cur.execute("UPDATE farms SET irrigation_type = 'well' WHERE LOWER(irrigation_type) = 'well'")
                cur.execute("UPDATE farms SET irrigation_type = 'canal' WHERE LOWER(irrigation_type) = 'canal'")
                cur.execute("UPDATE farms SET irrigation_type = 'drip' WHERE LOWER(irrigation_type) = 'drip' OR LOWER(irrigation_type) LIKE '%drip%'")
                cur.execute("UPDATE farms SET irrigation_type = 'borewell' WHERE LOWER(irrigation_type) = 'borewell'")
                cur.execute("UPDATE farms SET irrigation_type = 'rainfed' WHERE LOWER(irrigation_type) = 'rainfed'")
                cur.execute("UPDATE farms SET irrigation_type = 'sprinkler' WHERE LOWER(irrigation_type) = 'sprinkler'")
                cur.execute("UPDATE farms SET irrigation_type = 'pond_tank' WHERE LOWER(irrigation_type) IN ('pond', 'tank', 'pond/tank', 'pond_tank')")
                con.commit()
            finally:
                con.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        print("[START] Seeding AgriSync Database (Pune, Maharashtra region)...")

        # 1. Seed Crops
        crops_data = [
            {"name": "Wheat", "name_hi": "गेहूं", "name_mr": "गहू", "duration_days": 120, "category": "cereal"},
            {"name": "Rice", "name_hi": "चावल", "name_mr": "भात", "duration_days": 130, "category": "cereal"},
            {"name": "Maize", "name_hi": "मक्का", "name_mr": "मका", "duration_days": 105, "category": "cereal"},
            {"name": "Bajra", "name_hi": "बाजरा", "name_mr": "बाजरी", "duration_days": 85, "category": "cereal"},
            {"name": "Jowar", "name_hi": "ज्वार", "name_mr": "ज्वारी", "duration_days": 110, "category": "cereal"},
            {"name": "Tur/Arhar", "name_hi": "अरहर / तूर", "name_mr": "तूर", "duration_days": 150, "category": "pulse"},
            {"name": "Gram (Chana)", "name_hi": "चना", "name_mr": "हरभरा", "duration_days": 100, "category": "pulse"},
            {"name": "Moong", "name_hi": "मूंग", "name_mr": "मूग", "duration_days": 65, "category": "pulse"},
            {"name": "Urad", "name_hi": "उड़द", "name_mr": "उडीद", "duration_days": 70, "category": "pulse"},
            {"name": "Soybean", "name_hi": "सोयाबीन", "name_mr": "सोयाबीन", "duration_days": 100, "category": "oilseed"},
            {"name": "Groundnut", "name_hi": "मूंगफली", "name_mr": "भुईमूग", "duration_days": 115, "category": "oilseed"},
            {"name": "Mustard", "name_hi": "सरसों", "name_mr": "मोहरी", "duration_days": 110, "category": "oilseed"},
            {"name": "Cotton", "name_hi": "कपास", "name_mr": "कापूस", "duration_days": 160, "category": "cash crop"},
            {"name": "Sugarcane", "name_hi": "गन्ना", "name_mr": "ऊस", "duration_days": 360, "category": "cash crop"},
            {"name": "Onion", "name_hi": "प्याज", "name_mr": "कांदा", "duration_days": 120, "category": "vegetable"},
            {"name": "Tomato", "name_hi": "टमाटर", "name_mr": "टोमॅटो", "duration_days": 110, "category": "vegetable"},
            {"name": "Potato", "name_hi": "आलू", "name_mr": "बटाटा", "duration_days": 90, "category": "vegetable"},
            {"name": "Turmeric", "name_hi": "हल्दी", "name_mr": "हळद", "duration_days": 240, "category": "spice"},
            {"name": "Chilli", "name_hi": "हरी मिर्च", "name_mr": "मिरची", "duration_days": 150, "category": "spice"},
            {"name": "Ginger", "name_hi": "अदरक", "name_mr": "आले", "duration_days": 210, "category": "spice"},
        ]

        crops_map = {}
        for c in crops_data:
            stmt = select(Crop).where(Crop.name == c["name"])
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                existing = Crop(**c)
                db.add(existing)
                await db.flush()
            else:
                existing.name_hi = c.get("name_hi", existing.name_hi)
                existing.name_mr = c.get("name_mr", existing.name_mr)
                existing.duration_days = c.get("duration_days", existing.duration_days)
                existing.category = c.get("category", existing.category)
                await db.flush()
            crops_map[c["name"]] = existing

        print(f"  [OK] {len(crops_map)} Crops verified/seeded.")

        # 2. Seed Crop Stages (Minimum: sowing, vegetative, flowering, maturity/harvest)
        stages_data = {
            "Wheat": [
                ("Sowing & Germination", 0, 20),
                ("Crown Root Initiation & Vegetative", 21, 60),
                ("Flowering & Heading", 61, 90),
                ("Grain Filling & Maturity", 91, 120),
            ],
            "Rice": [
                ("Nursery & Transplanting", 0, 25),
                ("Tillering & Vegetative", 26, 60),
                ("Panicle Initiation & Flowering", 61, 95),
                ("Harvesting & Maturation", 96, 130),
            ],
            "Maize": [
                ("Sowing & Emergence", 0, 20),
                ("Vegetative & Knee High", 21, 50),
                ("Tasseling & Flowering", 51, 75),
                ("Grain Filling & Maturity", 76, 105),
            ],
            "Bajra": [
                ("Sowing & Seedling", 0, 18),
                ("Tillering & Vegetative", 19, 42),
                ("Flowering & Heading", 43, 62),
                ("Grain Filling & Maturity", 63, 85),
            ],
            "Jowar": [
                ("Sowing & Emergence", 0, 20),
                ("Vegetative Growth", 21, 55),
                ("Boot & Flowering", 56, 80),
                ("Grain Filling & Maturity", 81, 110),
            ],
            "Tur/Arhar": [
                ("Sowing & Germination", 0, 25),
                ("Branching & Vegetative", 26, 70),
                ("Flowering & Pod Setting", 71, 115),
                ("Pod Maturity & Harvesting", 116, 150),
            ],
            "Gram (Chana)": [
                ("Sowing & Emergence", 0, 20),
                ("Branching & Vegetative", 21, 45),
                ("Flowering & Pod Development", 46, 75),
                ("Pod Maturity & Harvesting", 76, 100),
            ],
            "Moong": [
                ("Sowing & Emergence", 0, 15),
                ("Vegetative Growth", 16, 32),
                ("Flowering & Pod Formation", 33, 48),
                ("Pod Ripening & Harvesting", 49, 65),
            ],
            "Urad": [
                ("Sowing & Emergence", 0, 15),
                ("Vegetative Growth", 16, 35),
                ("Flowering & Pod Development", 36, 52),
                ("Pod Maturity & Harvesting", 53, 70),
            ],
            "Soybean": [
                ("Sowing & Germination", 0, 20),
                ("Vegetative Growth", 21, 45),
                ("Flowering & Pod Formation", 46, 75),
                ("Pod Filling & Maturation", 76, 100),
            ],
            "Groundnut": [
                ("Sowing & Emergence", 0, 20),
                ("Vegetative & Pegging", 21, 50),
                ("Flowering & Pod Development", 51, 85),
                ("Pod Maturation & Harvesting", 86, 115),
            ],
            "Mustard": [
                ("Sowing & Emergence", 0, 20),
                ("Vegetative & Rosette", 21, 45),
                ("Flowering & Pod Formation", 46, 80),
                ("Siliqua Maturity & Harvesting", 81, 110),
            ],
            "Cotton": [
                ("Sowing & Seedling", 0, 30),
                ("Square Formation & Vegetative", 31, 70),
                ("Peak Flowering", 71, 120),
                ("Boll Bursting & Maturity", 121, 160),
            ],
            "Sugarcane": [
                ("Planting & Germination", 0, 35),
                ("Formative Tillering", 36, 120),
                ("Grand Growth", 121, 270),
                ("Ripening & Harvesting", 271, 360),
            ],
            "Onion": [
                ("Nursery & Transplanting", 0, 30),
                ("Vegetative Growth", 31, 65),
                ("Bulb Development & Flowering", 66, 95),
                ("Bulb Maturity & Harvesting", 96, 120),
            ],
            "Tomato": [
                ("Nursery & Transplanting", 0, 25),
                ("Vegetative & Branching", 26, 50),
                ("Flowering & Fruit Setting", 51, 80),
                ("Fruit Maturity & Harvesting", 81, 110),
            ],
            "Potato": [
                ("Planting & Sprouting", 0, 20),
                ("Vegetative Growth", 21, 45),
                ("Tuber Initiation & Flowering", 46, 70),
                ("Tuber Maturity & Harvesting", 71, 90),
            ],
            "Turmeric": [
                ("Planting & Sprouting", 0, 45),
                ("Vegetative & Tillering", 46, 120),
                ("Rhizome Development & Flowering", 121, 190),
                ("Rhizome Maturity & Harvesting", 191, 240),
            ],
            "Chilli": [
                ("Nursery & Transplanting", 0, 25),
                ("Vegetative Growth", 26, 55),
                ("Flowering & Fruit Setting", 56, 95),
                ("Fruit Maturity & Harvesting", 96, 150),
            ],
            "Ginger": [
                ("Planting & Emergence", 0, 40),
                ("Vegetative & Tillering", 41, 105),
                ("Rhizome Development & Flowering", 106, 170),
                ("Rhizome Maturity & Harvesting", 171, 210),
            ],
        }

        stages_map = {}
        for crop_name, stages in stages_data.items():
            crop_obj = crops_map[crop_name]
            expected_names = {s_name for s_name, _, _ in stages}
            stmt_stale = select(CropStage).where(CropStage.crop_id == crop_obj.id, CropStage.stage_name.not_in(expected_names))
            stale_stages = (await db.execute(stmt_stale)).scalars().all()
            for st in stale_stages:
                await db.delete(st)
            await db.flush()

            for s_name, start, end in stages:
                stmt = select(CropStage).where(CropStage.crop_id == crop_obj.id, CropStage.stage_name == s_name)
                st_obj = (await db.execute(stmt)).scalar_one_or_none()
                if not st_obj:
                    st_obj = CropStage(crop_id=crop_obj.id, stage_name=s_name, start_day=start, end_day=end)
                    db.add(st_obj)
                    await db.flush()
                else:
                    st_obj.start_day = start
                    st_obj.end_day = end
                    await db.flush()
                stages_map[(crop_name, s_name)] = st_obj

        print("  [OK] Crop Stages verified/seeded.")

        # 3. Seed Machine Types
        mtypes_data = [
            {"name": "Tractor", "name_hi": "ट्रैक्टर", "name_mr": "ट्रॅक्टर", "typical_rate_per_acre": 800.0, "mobilization_cost": 200.0},
            {"name": "Seed Drill", "name_hi": "सीड ड्रिल", "name_mr": "बियाणे पेरणी यंत्र", "typical_rate_per_acre": 600.0, "mobilization_cost": 150.0},
            {"name": "Sprayer", "name_hi": "स्प्रेयर", "name_mr": "फवारणी यंत्र", "typical_rate_per_acre": 350.0, "mobilization_cost": 100.0},
            {"name": "Harvester", "name_hi": "कंबाइन हार्वेस्टर", "name_mr": "हार्वेस्टर", "typical_rate_per_acre": 1800.0, "mobilization_cost": 500.0},
            {"name": "Rotavator", "name_hi": "रोटावेटर", "name_mr": "रोटाव्हेटर", "typical_rate_per_acre": 900.0, "mobilization_cost": 200.0},
            {"name": "Thresher", "name_hi": "थ्रेशर", "name_mr": "मळणी यंत्र", "typical_rate_per_acre": 700.0, "mobilization_cost": 150.0},
        ]

        mtypes_map = {}
        for mt in mtypes_data:
            stmt = select(MachineType).where(MachineType.name == mt["name"])
            existing_mt = (await db.execute(stmt)).scalar_one_or_none()
            if not existing_mt:
                existing_mt = MachineType(**mt)
                db.add(existing_mt)
                await db.flush()
            mtypes_map[mt["name"]] = existing_mt

        print(f"  [OK] {len(mtypes_map)} Machine Types verified/seeded.")

        # 4. Seed Crop Machine Mappings (covers every newly added crop reasonably)
        sample_source = "SAMPLE - verify with ICAR / state agriculture dept"
        crop_machine_rules = [
            # Wheat
            ("Wheat", "Sowing & Germination", "Rotavator", -10, 5),
            ("Wheat", "Sowing & Germination", "Seed Drill", 0, 5),
            ("Wheat", "Crown Root Initiation & Vegetative", "Sprayer", 25, 7),
            ("Wheat", "Grain Filling & Maturity", "Harvester", 110, 7),
            ("Wheat", "Grain Filling & Maturity", "Thresher", 121, 7),
            # Rice
            ("Rice", "Nursery & Transplanting", "Rotavator", -10, 5),
            ("Rice", "Nursery & Transplanting", "Seed Drill", 0, 5),
            ("Rice", "Tillering & Vegetative", "Sprayer", 30, 7),
            ("Rice", "Harvesting & Maturation", "Harvester", 120, 7),
            ("Rice", "Harvesting & Maturation", "Thresher", 131, 7),
            # Maize
            ("Maize", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Maize", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Maize", "Vegetative & Knee High", "Sprayer", 30, 7),
            ("Maize", "Grain Filling & Maturity", "Harvester", 95, 7),
            ("Maize", "Grain Filling & Maturity", "Thresher", 105, 7),
            # Bajra
            ("Bajra", "Sowing & Seedling", "Rotavator", -8, 5),
            ("Bajra", "Sowing & Seedling", "Seed Drill", 0, 5),
            ("Bajra", "Tillering & Vegetative", "Sprayer", 25, 7),
            ("Bajra", "Grain Filling & Maturity", "Harvester", 78, 7),
            ("Bajra", "Grain Filling & Maturity", "Thresher", 85, 7),
            # Jowar
            ("Jowar", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Jowar", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Jowar", "Vegetative Growth", "Sprayer", 35, 7),
            ("Jowar", "Grain Filling & Maturity", "Harvester", 100, 7),
            ("Jowar", "Grain Filling & Maturity", "Thresher", 110, 7),
            # Tur/Arhar
            ("Tur/Arhar", "Sowing & Germination", "Rotavator", -10, 5),
            ("Tur/Arhar", "Sowing & Germination", "Seed Drill", 0, 5),
            ("Tur/Arhar", "Flowering & Pod Setting", "Sprayer", 75, 7),
            ("Tur/Arhar", "Pod Maturity & Harvesting", "Harvester", 140, 7),
            ("Tur/Arhar", "Pod Maturity & Harvesting", "Thresher", 148, 7),
            # Gram (Chana)
            ("Gram (Chana)", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Gram (Chana)", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Gram (Chana)", "Flowering & Pod Development", "Sprayer", 50, 7),
            ("Gram (Chana)", "Pod Maturity & Harvesting", "Harvester", 92, 7),
            ("Gram (Chana)", "Pod Maturity & Harvesting", "Thresher", 98, 7),
            # Moong
            ("Moong", "Sowing & Emergence", "Rotavator", -7, 5),
            ("Moong", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Moong", "Vegetative Growth", "Sprayer", 20, 7),
            ("Moong", "Pod Ripening & Harvesting", "Thresher", 62, 7),
            # Urad
            ("Urad", "Sowing & Emergence", "Rotavator", -7, 5),
            ("Urad", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Urad", "Vegetative Growth", "Sprayer", 22, 7),
            ("Urad", "Pod Maturity & Harvesting", "Thresher", 68, 7),
            # Soybean
            ("Soybean", "Sowing & Germination", "Rotavator", -10, 5),
            ("Soybean", "Sowing & Germination", "Seed Drill", 0, 5),
            ("Soybean", "Flowering & Pod Formation", "Sprayer", 45, 7),
            ("Soybean", "Pod Filling & Maturation", "Harvester", 90, 7),
            ("Soybean", "Pod Filling & Maturation", "Thresher", 98, 7),
            # Groundnut
            ("Groundnut", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Groundnut", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Groundnut", "Vegetative & Pegging", "Sprayer", 30, 7),
            ("Groundnut", "Pod Maturation & Harvesting", "Tractor", 105, 7),
            ("Groundnut", "Pod Maturation & Harvesting", "Thresher", 115, 7),
            # Mustard
            ("Mustard", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Mustard", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Mustard", "Flowering & Pod Formation", "Sprayer", 50, 7),
            ("Mustard", "Siliqua Maturity & Harvesting", "Harvester", 100, 7),
            ("Mustard", "Siliqua Maturity & Harvesting", "Thresher", 108, 7),
            # Cotton
            ("Cotton", "Sowing & Seedling", "Rotavator", -10, 5),
            ("Cotton", "Sowing & Seedling", "Seed Drill", 0, 5),
            ("Cotton", "Square Formation & Vegetative", "Sprayer", 35, 7),
            ("Cotton", "Boll Bursting & Maturity", "Harvester", 145, 7),
            # Sugarcane
            ("Sugarcane", "Planting & Germination", "Rotavator", -10, 5),
            ("Sugarcane", "Planting & Germination", "Seed Drill", 0, 5),
            ("Sugarcane", "Formative Tillering", "Sprayer", 45, 7),
            ("Sugarcane", "Grand Growth", "Tractor", 150, 7),
            ("Sugarcane", "Ripening & Harvesting", "Harvester", 330, 10),
            # Onion
            ("Onion", "Nursery & Transplanting", "Rotavator", -10, 5),
            ("Onion", "Vegetative Growth", "Tractor", 40, 7),
            ("Onion", "Bulb Development & Flowering", "Sprayer", 70, 7),
            ("Onion", "Bulb Maturity & Harvesting", "Tractor", 115, 7),
            # Tomato
            ("Tomato", "Nursery & Transplanting", "Rotavator", -10, 5),
            ("Tomato", "Vegetative & Branching", "Sprayer", 35, 7),
            ("Tomato", "Flowering & Fruit Setting", "Sprayer", 60, 7),
            ("Tomato", "Fruit Maturity & Harvesting", "Tractor", 95, 7),
            # Potato
            ("Potato", "Planting & Sprouting", "Rotavator", -10, 5),
            ("Potato", "Planting & Sprouting", "Seed Drill", 0, 5),
            ("Potato", "Vegetative Growth", "Sprayer", 30, 7),
            ("Potato", "Tuber Maturity & Harvesting", "Tractor", 85, 7),
            # Turmeric
            ("Turmeric", "Planting & Sprouting", "Rotavator", -10, 5),
            ("Turmeric", "Vegetative & Tillering", "Tractor", 60, 7),
            ("Turmeric", "Rhizome Development & Flowering", "Sprayer", 130, 7),
            ("Turmeric", "Rhizome Maturity & Harvesting", "Tractor", 230, 7),
            # Chilli
            ("Chilli", "Nursery & Transplanting", "Rotavator", -10, 5),
            ("Chilli", "Vegetative Growth", "Sprayer", 40, 7),
            ("Chilli", "Flowering & Fruit Setting", "Sprayer", 70, 7),
            ("Chilli", "Fruit Maturity & Harvesting", "Tractor", 120, 7),
            # Ginger
            ("Ginger", "Planting & Emergence", "Rotavator", -10, 5),
            ("Ginger", "Vegetative & Tillering", "Tractor", 55, 7),
            ("Ginger", "Rhizome Development & Flowering", "Sprayer", 120, 7),
            ("Ginger", "Rhizome Maturity & Harvesting", "Tractor", 200, 7),
        ]

        for crop_n, stage_n, mtype_n, offset, window_days in crop_machine_rules:
            crop_o = crops_map[crop_n]
            stage_o = stages_map.get((crop_n, stage_n))
            mtype_o = mtypes_map[mtype_n]

            stmt = select(CropMachineMap).where(
                CropMachineMap.crop_id == crop_o.id,
                CropMachineMap.machine_type_id == mtype_o.id,
                CropMachineMap.stage_id == (stage_o.id if stage_o else None)
            )
            cm_obj = (await db.execute(stmt)).scalar_one_or_none()
            if not cm_obj:
                cm_obj = CropMachineMap(
                    crop_id=crop_o.id,
                    stage_id=stage_o.id if stage_o else None,
                    machine_type_id=mtype_o.id,
                    days_offset=offset,
                    window_days=window_days,
                    source=sample_source,
                )
                db.add(cm_obj)
            else:
                cm_obj.days_offset = offset
                cm_obj.window_days = window_days
                cm_obj.source = sample_source

        await db.flush()
        print("  [OK] Crop Machine Mappings verified/seeded.")

        # 5. Seed Nutrient Rules
        nutrient_rules_data = [
            # Wheat
            {"crop": "Wheat", "stage": "Crown Root Initiation & Vegetative", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Crown Root Initiation & Vegetative"}, "guidance": "Apply 60 kg/acre Urea during Crown Root Initiation (CRI) stage.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Wheat", "stage": "Crown Root Initiation & Vegetative", "nutrient": "Zinc", "condition": {"nutrient": "zinc", "level": ["low"], "stage": "Crown Root Initiation & Vegetative"}, "guidance": "Foliar spray of 0.5% Zinc Sulphate with 0.25% Lime.", "category": "Micro-Nutrient", "source": sample_source},
            # Rice
            {"crop": "Rice", "stage": "Tillering & Vegetative", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Tillering & Vegetative"}, "guidance": "Apply 40 kg/acre Single Super Phosphate (SSP) at tillering.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Rice", "stage": "Panicle Initiation & Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Panicle Initiation & Flowering"}, "guidance": "Top dress 25 kg/acre Muriate of Potash (MOP).", "category": "Fertilizer", "source": sample_source},
            # Cotton
            {"crop": "Cotton", "stage": "Sowing & Seedling", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Sowing & Seedling"}, "guidance": "Review nitrogen management during the seedling stage.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Cotton", "stage": "Square Formation & Vegetative", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Square Formation & Vegetative"}, "guidance": "Review phosphorus management before square formation.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Cotton", "stage": "Peak Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Peak Flowering"}, "guidance": "Review potassium management during peak flowering.", "category": "Fertilizer", "source": sample_source},
            # Soybean
            {"crop": "Soybean", "stage": "Vegetative Growth", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Review phosphorus management during early growth.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Soybean", "stage": "Flowering & Pod Formation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Formation"}, "guidance": "Review potassium management during flowering.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Soybean", "stage": "Pod Filling & Maturation", "nutrient": "Organic Carbon", "condition": {"nutrient": "organic_carbon", "level": ["low"], "stage": "Pod Filling & Maturation"}, "guidance": "Review organic matter management during pod filling.", "category": "Organic", "source": sample_source},
            # Sugarcane
            {"crop": "Sugarcane", "stage": "Planting & Germination", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Planting & Germination"}, "guidance": "Review nitrogen management during germination.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Sugarcane", "stage": "Formative Tillering", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Formative Tillering"}, "guidance": "Review phosphorus management during tillering.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Sugarcane", "stage": "Grand Growth", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Grand Growth"}, "guidance": "Review potassium management during grand growth.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Sugarcane", "stage": "Ripening & Harvesting", "nutrient": "Organic Carbon", "condition": {"nutrient": "organic_carbon", "level": ["low"], "stage": "Ripening & Harvesting"}, "guidance": "Review organic matter management before harvest.", "category": "Organic", "source": sample_source},
            # Maize
            {"crop": "Maize", "stage": "Vegetative & Knee High", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative & Knee High"}, "guidance": "Apply side-dress nitrogen fertilizer during knee-high stage.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Maize", "stage": "Tasseling & Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Tasseling & Flowering"}, "guidance": "Apply potassium to support tasseling and grain filling.", "category": "Fertilizer", "source": sample_source},
            # Bajra
            {"crop": "Bajra", "stage": "Tillering & Vegetative", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Tillering & Vegetative"}, "guidance": "Top dress nitrogen at 3-4 weeks after sowing during tillering.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Bajra", "stage": "Flowering & Heading", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Flowering & Heading"}, "guidance": "Ensure adequate phosphorus availability during earhead emergence.", "category": "Fertilizer", "source": sample_source},
            # Jowar
            {"crop": "Jowar", "stage": "Vegetative Growth", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Split application of nitrogen during peak vegetative stage.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Jowar", "stage": "Boot & Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Boot & Flowering"}, "guidance": "Apply potash at boot stage for strong stalk and earhead filling.", "category": "Fertilizer", "source": sample_source},
            # Tur/Arhar
            {"crop": "Tur/Arhar", "stage": "Branching & Vegetative", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Branching & Vegetative"}, "guidance": "Apply phosphorus and Rhizobium biofertilizer to promote root nodulation.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Tur/Arhar", "stage": "Flowering & Pod Setting", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Setting"}, "guidance": "Apply foliar potassium spray to minimize flower drop and enhance pod fill.", "category": "Fertilizer", "source": sample_source},
            # Gram (Chana)
            {"crop": "Gram (Chana)", "stage": "Branching & Vegetative", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Branching & Vegetative"}, "guidance": "Apply Single Super Phosphate (SSP) at branching to enhance root nodules.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Gram (Chana)", "stage": "Flowering & Pod Development", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Development"}, "guidance": "Apply 2% DAP or Potassium foliar spray during pod formation.", "category": "Fertilizer", "source": sample_source},
            # Moong
            {"crop": "Moong", "stage": "Vegetative Growth", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Ensure adequate phosphorus and sulfur for nodule development.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Moong", "stage": "Flowering & Pod Formation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Formation"}, "guidance": "Foliar nutrient spray to prevent flower drop during early pod set.", "category": "Fertilizer", "source": sample_source},
            # Urad
            {"crop": "Urad", "stage": "Vegetative Growth", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Basal phosphorus application promotes rapid root growth and nodulation.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Urad", "stage": "Flowering & Pod Development", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Development"}, "guidance": "Apply foliar potassium spray at pod setting for uniform grain fill.", "category": "Fertilizer", "source": sample_source},
            # Groundnut
            {"crop": "Groundnut", "stage": "Vegetative & Pegging", "nutrient": "Calcium", "condition": {"nutrient": "calcium", "level": ["low"], "stage": "Vegetative & Pegging"}, "guidance": "Apply gypsum (200 kg/acre) during pegging for pod filling and shell hardening.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Groundnut", "stage": "Flowering & Pod Development", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Flowering & Pod Development"}, "guidance": "Maintain balanced soil phosphorus to support continuous peg development.", "category": "Fertilizer", "source": sample_source},
            # Mustard
            {"crop": "Mustard", "stage": "Vegetative & Rosette", "nutrient": "Sulfur", "condition": {"nutrient": "sulfur", "level": ["low"], "stage": "Vegetative & Rosette"}, "guidance": "Apply sulfur (20 kg/acre) to boost oil content and vegetative vigor.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Mustard", "stage": "Flowering & Pod Formation", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Flowering & Pod Formation"}, "guidance": "Top dress nitrogen with first flowering irrigation.", "category": "Fertilizer", "source": sample_source},
            # Onion
            {"crop": "Onion", "stage": "Vegetative Growth", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Apply split dose of nitrogen 30 days after transplanting.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Onion", "stage": "Bulb Development & Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Bulb Development & Flowering"}, "guidance": "Apply Sulfate of Potash (SOP) to boost bulb weight and storage quality.", "category": "Fertilizer", "source": sample_source},
            # Tomato
            {"crop": "Tomato", "stage": "Vegetative & Branching", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative & Branching"}, "guidance": "Apply balanced NPK fertigation during vegetative branching.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Tomato", "stage": "Flowering & Fruit Setting", "nutrient": "Calcium", "condition": {"nutrient": "calcium", "level": ["low"], "stage": "Flowering & Fruit Setting"}, "guidance": "Foliar spray of Calcium Nitrate to prevent blossom end rot.", "category": "Micro-Nutrient", "source": sample_source},
            # Potato
            {"crop": "Potato", "stage": "Vegetative Growth", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Top dress nitrogen during first earthing up at 30 days.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Potato", "stage": "Tuber Initiation & Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Tuber Initiation & Flowering"}, "guidance": "Apply MOP or SOP during tuber bulking to maximize tuber size.", "category": "Fertilizer", "source": sample_source},
            # Turmeric
            {"crop": "Turmeric", "stage": "Vegetative & Tillering", "nutrient": "Organic Carbon", "condition": {"nutrient": "organic_carbon", "level": ["low"], "stage": "Vegetative & Tillering"}, "guidance": "Apply well-decomposed FYM/compost and neem cake at tillering.", "category": "Organic", "source": sample_source},
            {"crop": "Turmeric", "stage": "Rhizome Development & Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Rhizome Development & Flowering"}, "guidance": "Apply potassium and micronutrients to maximize rhizome size and curcumin.", "category": "Fertilizer", "source": sample_source},
            # Chilli
            {"crop": "Chilli", "stage": "Vegetative Growth", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Apply nitrogen fertigation at 3-4 weeks after transplanting.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Chilli", "stage": "Flowering & Fruit Setting", "nutrient": "Boron", "condition": {"nutrient": "boron", "level": ["low"], "stage": "Flowering & Fruit Setting"}, "guidance": "Foliar spray of Boron (0.1%) to reduce flower dropping and enhance fruit set.", "category": "Micro-Nutrient", "source": sample_source},
            # Ginger
            {"crop": "Ginger", "stage": "Vegetative & Tillering", "nutrient": "Organic Carbon", "condition": {"nutrient": "organic_carbon", "level": ["low"], "stage": "Vegetative & Tillering"}, "guidance": "Apply green manure mulch and compost at first earthing up.", "category": "Organic", "source": sample_source},
            {"crop": "Ginger", "stage": "Rhizome Development & Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Rhizome Development & Flowering"}, "guidance": "Apply potash at rhizome development for optimal yield and fiber quality.", "category": "Fertilizer", "source": sample_source},
        ]

        for nr in nutrient_rules_data:
            crop_o = crops_map[nr["crop"]]
            stage_o = stages_map.get((nr["crop"], nr["stage"]))
            stmt = select(NutrientRule).where(
                NutrientRule.crop_id == crop_o.id,
                NutrientRule.nutrient == nr["nutrient"],
                NutrientRule.guidance_text == nr["guidance"]
            )
            nr_obj = (await db.execute(stmt)).scalar_one_or_none()
            if not nr_obj:
                nr_obj = NutrientRule(
                    crop_id=crop_o.id,
                    stage_id=stage_o.id if stage_o else None,
                    nutrient=nr["nutrient"],
                    condition_json=nr["condition"],
                    guidance_text=nr["guidance"],
                    input_category=nr["category"],
                    source=nr["source"],
                )
                db.add(nr_obj)
            else:
                nr_obj.stage_id = stage_o.id if stage_o else None
                nr_obj.condition_json = nr["condition"]
                nr_obj.input_category = nr["category"]
                nr_obj.source = nr["source"]

        await db.flush()
        print("  [OK] Nutrient Rules verified/seeded (tagged with ICAR/State Dept source).")


        # 6. Seed 30 Farmers
        farmer_names = [
            "Ramesh Patil", "Suresh Deshmukh", "Ganesh Pawar", "Anand Kadam", "Dnyaneshwar Shinde",
            "Vijay Gaikwad", "Santosh Jadhav", "Nitin Mane", "Sachin Bhosale", "Sunil Jagtap",
            "Prakash Chavhan", "Mahadev Thorat", "Balasaheb More", "Deepak Mohite", "Popat Kale",
            "Baban Salunkhe", "Laxman Raut", "Pandurang Shelke", "Shivaji Nimbalkar", "Vikas Phadtare",
            "Tukaram Gawade", " Maruti Hande", "Dattatray Wagh", "Kishor Bankar", "Eknath Khade",
            "Gopal Belhekar", "Navnath Bandal", "Ashok Dhamdhere", "Yogesh Bandal", "Prashant Katke"
        ]

        farmer_users = []
        for i, name in enumerate(farmer_names, 1):
            phone = f"+9198220{i:05d}"
            stmt = select(User).where(User.phone == phone)
            user_obj = (await db.execute(stmt)).scalar_one_or_none()
            if not user_obj:
                user_obj = User(name=name.strip(), phone=phone, role="farmer", language=random.choice(["en", "hi", "mr"]))
                db.add(user_obj)
                await db.flush()

                loc_data = PUNE_LOCATIONS[i % len(PUNE_LOCATIONS)]
                lat, lon = random_offset_coords(loc_data[2], loc_data[3], radius_km=15)
                point_wkt = f"POINT({lon} {lat})"

                profile = FarmerProfile(
                    user_id=user_obj.id,
                    village=loc_data[0],
                    district=loc_data[1],
                    state="Maharashtra",
                    location=point_wkt,
                    total_area_acres=round(random.uniform(1.5, 8.5), 1)
                )
                db.add(profile)
                await db.flush()

            farmer_users.append(user_obj)

        print(f"  [OK] {len(farmer_users)} Farmers & Profiles verified/seeded.")

        # 7. Seed Farms & Soil Tests
        farm_ids = []
        for farmer in farmer_users:
            stmt = select(Farm).where(Farm.farmer_id == farmer.id)
            existing_farm = (await db.execute(stmt)).scalar_one_or_none()
            if not existing_farm:
                crop = random.choice(list(crops_map.values()))
                sow_date = date.today() - timedelta(days=random.randint(10, 80))
                farm_obj = Farm(
                    farmer_id=farmer.id,
                    crop_id=crop.id,
                    sowing_date=sow_date,
                    area_acres=round(random.uniform(1.0, 4.0), 1),
                    soil_type=random.choice(["Black Cotton", "Loam", "Clay Loam"]),
                    current_stage=random.choice(["Vegetative", "Sowing", "Flowering"]),
                    irrigation_type=random.choice(["Drip", "Canal", "Well"])
                )
                db.add(farm_obj)
                await db.flush()

                soil_test = SoilTest(
                    farm_id=farm_obj.id,
                    ph=round(random.uniform(6.2, 7.8), 2),
                    nitrogen=round(random.uniform(210.0, 320.0), 1),
                    phosphorus=round(random.uniform(12.0, 28.0), 1),
                    potassium=round(random.uniform(140.0, 250.0), 1),
                    organic_carbon=round(random.uniform(0.4, 0.8), 2),
                    tested_on=date.today() - timedelta(days=random.randint(15, 120))
                )
                db.add(soil_test)
                await db.flush()
                farm_ids.append(farm_obj.id)
            else:
                farm_ids.append(existing_farm.id)

        print("  [OK] Farms & Soil Tests verified/seeded.")

        # 8. Seed 10 Providers & 20 Machines
        provider_names = [
            "Krishi Seva Kendra Pune", "Maval Farmers Producer Co", "Shirur CHC Hub",
            "Baramati Agro Equipment", "Purandar Machinery Syndicate", "Junnar Tractor Hire",
            "Indapur Farmer Group", "Daund Agri Machinery", "Haveli Custom Hiring", "Mulshi Agro Tech"
        ]

        machines_list = []
        for i, name in enumerate(provider_names, 1):
            phone = f"+9199220{i:05d}"
            stmt = select(User).where(User.phone == phone)
            p_user = (await db.execute(stmt)).scalar_one_or_none()
            if not p_user:
                p_user = User(name=name, phone=phone, role="provider", language="mr")
                db.add(p_user)
                await db.flush()

                provider_profile = Provider(
                    user_id=p_user.id,
                    org_type=random.choice(["owner", "FPO", "CHC", "service"]),
                    verified=True
                )
                db.add(provider_profile)
                await db.flush()

            # Add 2 machines per provider
            for m_idx in range(2):
                mt_obj = list(mtypes_map.values())[(i * 2 + m_idx) % len(mtypes_map)]
                stmt_m = select(Machine).where(
                    Machine.provider_id == p_user.id,
                    Machine.machine_type_id == mt_obj.id
                )
                m_obj = (await db.execute(stmt_m)).scalar_one_or_none()
                if not m_obj:
                    loc_data = PUNE_LOCATIONS[i % len(PUNE_LOCATIONS)]
                    m_lat, m_lon = random_offset_coords(loc_data[2], loc_data[3], radius_km=12)
                    m_wkt = f"POINT({m_lon} {m_lat})"

                    m_obj = Machine(
                        provider_id=p_user.id,
                        machine_type_id=mt_obj.id,
                        location=m_wkt,
                        rate_per_acre=mt_obj.typical_rate_per_acre,
                        available_from=date.today(),
                        available_to=date.today() + timedelta(days=60),
                        verified=True,
                        rating=round(random.uniform(4.0, 4.9), 1)
                    )
                    db.add(m_obj)
                    await db.flush()

                machines_list.append(m_obj)

        print(f"  [OK] 10 Providers & {len(machines_list)} Machines verified/seeded around Pune.")

        # 9. Seed 8 Input Sellers
        sellers_data = [
            ("Pune Krishi Udyog", 18.5204, 73.8567, ["seeds", "fertilizers"]),
            ("Haveli Seed Store", 18.4500, 73.8000, ["seeds", "pesticides"]),
            ("Shirur Kisan Bazaar", 18.8300, 74.3700, ["fertilizers", "implements"]),
            ("Baramati Bio-Inputs", 18.1500, 74.5800, ["organic", "bio-fertilizers"]),
            ("Junnar Agri Care", 19.2000, 73.8700, ["pesticides", "seeds"]),
            ("Purandar Farmer Depot", 18.2800, 73.9700, ["fertilizers", "seeds"]),
            ("Maval Agri World", 18.7500, 73.5300, ["seeds", "implements"]),
            ("Mulshi Organic Hub", 18.5000, 73.5100, ["organic", "fertilizers"]),
        ]

        for s_name, s_lat, s_lon, s_cats in sellers_data:
            stmt = select(InputSeller).where(InputSeller.name == s_name)
            s_obj = (await db.execute(stmt)).scalar_one_or_none()
            if not s_obj:
                point_wkt = f"POINT({s_lon} {s_lat})"
                s_obj = InputSeller(
                    name=s_name,
                    location=point_wkt,
                    verified=True,
                    categories=s_cats
                )
                db.add(s_obj)

        await db.flush()
        print("  [OK] 8 Input Sellers verified/seeded.")

        # 10. Seed Sample Booking Group & Members (Testing Group Constraint)
        if machines_list and farmer_users:
            sample_machine = machines_list[0]
            creator_farmer = farmer_users[0]
            stmt_bg = select(BookingGroup).where(BookingGroup.created_by == creator_farmer.id)
            bg_obj = (await db.execute(stmt_bg)).scalar_one_or_none()
            if not bg_obj:
                bg_obj = BookingGroup(
                    machine_id=sample_machine.id,
                    scheduled_date=date.today() + timedelta(days=5),
                    status="open",
                    min_farmers=2,
                    max_acres=20.0,
                    created_by=creator_farmer.id
                )
                db.add(bg_obj)
                await db.flush()

                # Add 2 distinct members
                for f_idx in range(2):
                    f_user = farmer_users[f_idx]
                    stmt_farm = select(Farm).where(Farm.farmer_id == f_user.id)
                    f_farm = (await db.execute(stmt_farm)).scalar_one()
                    
                    gm_obj = GroupMember(
                        group_id=bg_obj.id,
                        farmer_id=f_user.id,
                        farm_id=f_farm.id,
                        acres=2.5,
                        share_amount=2000.0,
                        status="joined"
                    )
                    db.add(gm_obj)
                await db.flush()

        await db.commit()
        print("[SUCCESS] AgriSync Database Seeding Completed Successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
