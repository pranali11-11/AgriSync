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
    CropMachineMap, BookingGroup, GroupMember, InputSeller, Notification, Scheme
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
                _add_col("crop_stages", "stage_description TEXT", "stage_description")
                _add_col("crop_stages", "source VARCHAR(255) DEFAULT 'SAMPLE - verify with ICAR / state agriculture dept' NOT NULL", "source")
                _add_col("farms", "irrigation_type_note TEXT", "irrigation_type_note")
                cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schemes'")
                if cur.fetchone():
                    _add_col("schemes", "short_description_hi TEXT", "short_description_hi")
                    _add_col("schemes", "short_description_mr TEXT", "short_description_mr")
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

        # 2. Seed Crop Stages (Complete, contiguous ICAR lifecycle stages covering day 0 to duration_days)
        sample_source = "SAMPLE - verify with ICAR / state agriculture dept"
        stages_data = {
            "Wheat": [
                ("Sowing", 0, 5, "Seeds are drilled 3-5 cm deep into a fine, moist seedbed with adequate soil aeration. Ensure proper soil moisture for rapid imbibition and protect seeds from soil pests and birds."),
                ("Germination", 5, 15, "Coleoptiles emerge through the soil surface and primary seminal roots anchor the seedlings. Check for uniform seedling emergence, prevent surface soil crusting, and watch for damping-off."),
                ("Tillering", 15, 40, "Crown roots establish and lateral vegetative tillers proliferate from basal nodes. Critical period for nitrogen top-dressing and irrigation; monitor for moisture stress and early weed competition."),
                ("Jointing", 40, 65, "Stem internodes elongate rapidly and the embryonic head ascends within the leaf sheath. Nutrient and water demand increases significantly; watch for yellow rust, powdery mildew, and stem borers."),
                ("Flowering", 65, 85, "Spikes emerge completely (heading) followed by anthesis and pollination across florets. High temperatures or water stress cause floret sterility; monitor for head blight and aphid colonies."),
                ("Grain Filling", 85, 105, "Carbohydrates translocate into kernels through milk and dough stages, determining kernel weight. Watch for terminal heat stress, flag leaf rust, and maintain mild soil moisture."),
                ("Maturity", 105, 120, "Grains harden into hard dough, foliage turns golden yellow, and moisture drops below 14 percent. Watch for shattering and lodging from late winds; schedule harvest during clear dry weather."),
            ],
            "Rice": [
                ("Nursery", 0, 20, "Seeds germinate in nursery beds and produce green seedlings with 3-4 leaves over three weeks. Maintain shallow standing water; watch for seedling blast and iron chlorosis."),
                ("Transplanting & Establishment", 20, 35, "Seedlings are transplanted into puddled fields and re-establish root anchoring in mud. Keep 2-3 cm water depth; monitor for transplanting shock, snails, and seedling mortality."),
                ("Tillering", 35, 65, "Basal vegetative tillers multiply rapidly, determining total productive panicle capacity per hill. Watch for stem borer (dead hearts), sheath blight, and apply split nitrogen doses."),
                ("Panicle Initiation", 65, 85, "Internodes elongate and embryonic panicles differentiate inside the swollen boot leaf sheath. Maintain continuous shallow standing water; monitor for boot leaf caterpillars and leaf blast."),
                ("Flowering & Heading", 85, 105, "Panicles emerge from flag leaf boots followed by anthesis and pollination in morning hours. Hot dry winds cause spikelet sterility; inspect for gundhi bugs feeding on tender florets."),
                ("Grain Filling", 105, 120, "Pollinated spikelets accumulate starch through milk and dough phases, bending panicles downward. Gradually drain water 10-14 days before harvest; watch for neck blast and rodents."),
                ("Maturity & Harvest", 120, 130, "Grains harden to 20 percent moisture and turn golden yellow as straw senesces completely. Harvest promptly during dry weather to prevent grain shattering and bird predation."),
            ],
            "Maize": [
                ("Sowing & Germination", 0, 10, "Seeds imbibe water and radicles emerge followed by coleoptiles pushing through warm soil. Ensure adequate seedbed moisture; watch for soil crusting and wireworm or cutworm attack."),
                ("Vegetative & Knee High", 10, 35, "Plants expand broad leaves rapidly and reach knee-high stage with bracing prop roots. Apply nitrogen top-dressing and interculture; monitor closely for fall armyworm in leaf whorls."),
                ("Tasseling & Silking", 35, 60, "Staminate tassels shed pollen while receptive silks emerge from ear shoots below. Moisture stress during silking delays silk emergence and severely reduces kernel set; watch for earworms."),
                ("Grain Filling", 60, 90, "Kernels swell through blister, milk, and dent phases with rapid starch deposition in cobs. Maintain consistent irrigation; inspect for leaf blight, stalk rot, and cob borers."),
                ("Maturity & Harvest", 90, 105, "A black abscission layer forms at kernel tips signaling physiological maturity as husks dry. Harvest cobs when kernel moisture falls below 15-18 percent to avoid ear mold."),
            ],
            "Bajra": [
                ("Sowing & Seedling", 0, 10, "Small seeds germinate rapidly in warm soil with thin seedlings emerging in 3-5 days. Thin seedlings early to optimal intra-row spacing; protect from shoot fly and soil crusting."),
                ("Tillering & Vegetative", 10, 30, "Basal tillers arise alongside deep drought-tolerant root system and expanding leaf blades. Apply light hoeing and first nitrogen dose; monitor for stem borer and downy mildew."),
                ("Booting & Flowering", 30, 50, "Cylindrical panicles swell within flag leaves and emerge with protogynous blossoms shedding pollen. Warm dry weather favors pollination; watch for ergot honeydew exudation and shoot bugs."),
                ("Grain Filling", 50, 70, "Grains accumulate starch rapidly inside glumes, progressing from milk to dough consistency. Maintain weed-free fields; protect developing ears from head caterpillars and bird flocks."),
                ("Maturity & Harvest", 70, 85, "Grains turn grayish-brown with dark tips and attain full hardness while foliage senesces. Harvest earheads before over-drying to avoid grain shattering in strong winds."),
            ],
            "Jowar": [
                ("Sowing & Emergence", 0, 12, "Seeds germinate in warm moist seedbed, producing seminal roots and healthy green coleoptiles. Watch for shoot fly dead-hearts in the first two weeks and avoid heavy crusting rains."),
                ("Vegetative Growth", 12, 40, "Plants produce broad waxy leaves and establish deep fibrous roots capable of enduring dry spells. Perform intercultivation and top-dress nitrogen; inspect for fall armyworm and stem borers."),
                ("Booting & Flowering", 40, 65, "Panicles swell inside swollen flag leaf boots and emerge for pollination under bright sunshine. Flowering proceeds from tip to base; watch for midge fly and earhead bugs sucking sap."),
                ("Grain Filling", 65, 90, "Kernels swell through milk, soft dough, and hard dough stages with high carbohydrate deposition. Watch for grain mold during unseasonal rains, head worms, and bird damage."),
                ("Maturity & Harvest", 90, 110, "Black layer forms at grain hilum indicating physiological maturity as grain moisture falls below 15 percent. Harvest heads promptly to prevent lodging and grain weathering."),
            ],
            "Tur/Arhar": [
                ("Sowing & Germination", 0, 15, "Deep taproot develops as cotyledons emerge and establish sturdy seedlings in well-drained soil. Inoculate with Rhizobium; watch for waterlogging which induces Phytophthora blight."),
                ("Branching & Vegetative", 15, 60, "Primary and secondary sympodial branches proliferate, building a dense bush and deep root network. Keep rows weed-free during slow initial growth; monitor for leaf webbers and blister beetles."),
                ("Pre-Flowering & Budding", 60, 90, "Flower buds differentiate at branch terminals as vegetative extension slows and canopy closes. Roots extract subsoil water; inspect for Helicoverpa armigera moth activity and wilt symptoms."),
                ("Flowering & Pod Setting", 90, 120, "Yellow flowers blossom profusely and bees effect pollination with nascent pod formation. Pigeonpea naturally sheds excess blossoms; watch for pod borers and pod fly attacking young pods."),
                ("Pod Filling", 120, 140, "Seeds swell inside green pods, accumulating high protein content as leaves begin yellowing. Subsoil moisture dictates seed weight; watch for spotted pod borer webbing and pod bug damage."),
                ("Maturity & Harvest", 140, 150, "Pods turn brown and dry with seeds rattling inside shells upon shaking, signaling harvest readiness. Cut plants when 80 percent of pods are mature to prevent pod shattering in dry weather."),
            ],
            "Gram (Chana)": [
                ("Sowing & Emergence", 0, 12, "Hypogeal germination pushes compound pinnate plumules above cool moist soil with deep taproots. Ensure proper sowing depth and moisture; watch for collar rot in waterlogged seedbeds."),
                ("Branching & Vegetative", 12, 38, "Basal branches proliferate into a dense semi-erect canopy with active root nodulation. Nip apical shoot tips at 30-35 days to encourage branching; monitor for cutworms and weeds."),
                ("Flowering & Pod Initiation", 38, 62, "Pink or white flowers bloom along leaf axils and self-pollinate to produce tiny flat green pods. Cold waves or heat spikes cause flower drop; watch closely for Helicoverpa caterpillar feeding."),
                ("Pod Development & Filling", 62, 85, "Pods swell with 1-2 developing seeds accumulating high protein reserves under sunny weather. Avoid heavy irrigation during pod filling; monitor for pod borer larvae and dry root rot."),
                ("Maturity & Harvest", 85, 100, "Plants turn straw yellow, leaves drop, and dry pods rattle upon shaking as moisture drops to 10-12 percent. Harvest in early morning to prevent pod shattering and store grain dry."),
            ],
            "Moong": [
                ("Sowing & Emergence", 0, 8, "Epigeal germination brings cotyledons above warm soil within 3 to 5 days with active rooting. Protect tender seedlings from soil crusting, damping off, and early flea beetles."),
                ("Vegetative Growth", 8, 25, "Trifoliate leaves expand rapidly and branches establish quick ground cover suppressing weeds. Symbiotic nodules fix nitrogen; watch for yellow mosaic virus spread by whiteflies."),
                ("Flowering & Pod Formation", 25, 42, "Yellow flowers bloom in dense axillary racemes and set slender green cylindrical pods. High humidity and sunshine favor pod set; watch for Maruca webbers, blossom thrips, and borers."),
                ("Pod Filling", 42, 55, "Seeds swell rapidly inside pods, accumulating starch and protein while turning dark green. Ensure light moisture without water stagnation; inspect for pod bugs and powdery mildew."),
                ("Maturity & Harvesting", 55, 65, "Pods turn blackish-brown and dry uniformly across the canopy with mature seeds inside. Pick or combine mature pods promptly to prevent severe field shattering losses."),
            ],
            "Urad": [
                ("Sowing & Emergence", 0, 8, "Hypogeal emergence produces sturdy sprouts and primary root anchors within a week in moist soil. Avoid water stagnation; watch for seedling blight, cutworms, and flea beetles."),
                ("Vegetative Growth", 8, 28, "Hairy trifoliate leaves and spreading branches develop rapidly with active Rhizobium nodules. Canopy shades soil; monitor for whiteflies transmitting yellow mosaic virus and leafhoppers."),
                ("Flowering & Pod Initiation", 28, 45, "Yellow blossoms open along short racemes, self-pollinate, and set clusters of hairy green pods. Maintain moderate soil moisture; inspect for blossom thrips and spotted pod borer."),
                ("Pod Filling", 45, 60, "Pods swell and elongate as cylindrical black seeds accumulate starch and protein reserves. Bright sunny days support seed filling; watch for pod sucking bugs and anthracnose lesions."),
                ("Maturity & Harvesting", 60, 70, "Pods turn dark brown or black, becoming crisp as seeds reach harvest moisture under 12 percent. Harvest when 80 percent of pods turn black, preferably in morning to avoid shattering."),
            ],
            "Soybean": [
                ("Sowing & Germination", 0, 10, "Epigeal germination pushes cotyledons above ground followed by unifoliate and trifoliate leaves. Optimal sowing depth of 3-4 cm prevents seed rot; watch for collar rot and blue beetle."),
                ("Vegetative Growth", 10, 35, "Vigorous branching and node formation occur alongside prolific Bradyrhizobium root nodulation. Canopy closes over rows; watch for stem fly maggots, girdle beetles, and semiloopers."),
                ("Flowering & Pod Initiation", 35, 55, "Purple or white flowers open at leaf axils and produce flat nascent pods under sunny skies. Moisture stress triggers severe flower and pod drop; inspect for Spodoptera defoliators."),
                ("Pod Filling", 55, 80, "Seeds expand rapidly inside green pods, accumulating high oil and protein reserves. This is the most water-sensitive phase; watch for stink bugs piercing pods and rust spots."),
                ("Maturity & Harvest", 80, 100, "Leaves turn yellow and drop off, leaving brown stems bearing dry rattling pods. Harvest when seed moisture reaches 13-14 percent to prevent pod shattering in hot afternoons."),
            ],
            "Groundnut": [
                ("Sowing & Emergence", 0, 12, "Seeds germinate in friable sandy-loam soil, pushing four-leaved seedlings through the surface. Ensure warm loose soil; watch for collar rot, Aspergillus crown rot, and white grubs."),
                ("Vegetative Growth", 12, 35, "Main stem and lateral branches spread with vigorous root nodulation and root elongation. Keep soil loose and weed-free through interculture before flowering; watch for leaf miner and thrips."),
                ("Flowering & Pegging", 35, 60, "Yellow flowers self-pollinate and wither as geotropic pegs (gynophores) elongate downward into soil. Maintain friable moist soil for peg entry; avoid deep hoeing and watch for tikka leaf spot."),
                ("Pod Development", 60, 95, "Peg tips swell horizontally underground to form pods, depositing calcium and kernel oil reserves. Apply gypsum in pegging zone; inspect for subterranean termites and stem rot."),
                ("Maturity & Harvest", 95, 115, "Pods develop reticulated veins with dark inner shell markings indicating kernel maturity. Lift vines when test pods show dark interiors; sun-dry harvested pods to 8 percent moisture."),
            ],
            "Mustard": [
                ("Sowing & Emergence", 0, 10, "Seeds germinate in moist seedbed and cotyledons emerge within 3-5 days in cool weather. Thin seedlings to 10-15 cm spacing at 10 days; watch for flea beetles and sawfly larvae."),
                ("Vegetative & Rosette", 10, 35, "Plants form a spreading basal rosette of broad lobed leaves and deep taproots explore subsoil. Apply first nitrogen top-dressing; inspect tender shoots for mustard aphids and white rust."),
                ("Flowering & Heading", 35, 65, "Bright yellow racemes bloom across the field, attracting honeybees for cross-pollination. High bee activity enhances pod set; watch for aphid surges and avoid daytime insecticide sprays."),
                ("Siliqua & Pod Filling", 65, 90, "Slender green siliquae swell with developing seeds accumulating high oil percentage. Maintain soil moisture until seed filling ends; monitor for alternaria blight and powdery mildew."),
                ("Maturity & Harvest", 90, 110, "Siliquae turn golden brown and seeds rattle inside dry brittle pods when shaken gently. Harvest in early morning when pods are damp to prevent field shattering losses."),
            ],
            "Cotton": [
                ("Sowing & Seedling", 0, 20, "Seeds germinate epigeally and produce cordate cotyledons followed by true lobed leaves. Deep vertical taproots establish quickly; watch for thrips, jassids, and damping-off."),
                ("Vegetative Growth", 20, 50, "Monopodial and sympodial branches proliferate, building a sturdy bush with broad green foliage. Apply balanced fertilizer and weed inter-rows; monitor for whitefly, jassids, and aphids."),
                ("Square Formation", 50, 75, "Pyramidal flower buds (squares) enclosed in serrated bracts develop along fruiting branches. Maintain moisture to prevent square shedding; watch for spotted bollworms and mirid bugs."),
                ("Peak Flowering", 75, 110, "Creamy white flowers bloom daily, turning pink post-fertilization as young bolls develop rapidly. Peak water and nutrient demand; watch for pink bollworm larvae in flowers and bacterial blight."),
                ("Boll Development", 110, 140, "Green bolls expand to maximum size, depositing dense cellulose walls inside lint fibers. Maintain regular irrigation; watch for pink bollworm tunneling into bolls and fungal boll rots."),
                ("Boll Bursting & Harvest", 140, 160, "Bolls crack open along sutures and fluff into gleaming white lint ready for manual picking. Pick in multiple clean passes during dry weather; keep picked cotton free of dry leaf trash."),
            ],
            "Sugarcane": [
                ("Planting & Germination", 0, 45, "Sett buds sprout through soil cover, developing sett roots and primary shoots in warm furrows. Maintain furrow moisture; inspect for early shoot borer dead-hearts and termite damage."),
                ("Formative Tillering", 45, 120, "Basal nodes produce copious tillers while permanent shoot roots establish deep anchorage. Earthing-up and split nitrogen fertilizing convert tillers into robust canes; monitor for shoot borers."),
                ("Grand Growth", 120, 270, "Canes elongate rapidly, accumulating heavy stalk diameter, internodes, and lush green biomass. Peak irrigation and nutrient uptake during monsoon; tie canes to prevent wind lodging."),
                ("Ripening", 270, 330, "Vegetative growth slows and sucrose synthesis concentrates in stalk internodes during cool weather. Withhold heavy irrigation to enhance juice purity and Brix; monitor for scale insects."),
                ("Harvest & Maturation", 330, 360, "Canes reach peak sucrose Brix above 18-20 percent uniformly from bottom to top nodes. Cut canes flush with ground level and deliver to crushing mills within 24 hours of harvest."),
            ],
            "Onion": [
                ("Nursery & Transplanting", 0, 30, "Seedlings raised in nursery beds for 6 weeks are trimmed and transplanted into moist field beds. Seedlings root quickly and resume tubular leaf growth; watch for damping off and thrips."),
                ("Vegetative Growth", 30, 65, "Plants produce successive cylindrical hollow leaves building photosynthetic reserves for bulbing. Leaf count dictates bulb size; inspect leaf axils for thrips and purple blotch lesions."),
                ("Bulb Initiation", 65, 85, "Leaf bases begin swelling into fleshy scales in response to photoperiod and temperature triggers. Provide balanced potash and light frequent irrigation; watch for downy mildew and thrips."),
                ("Bulb Development", 85, 105, "Bulbs enlarge rapidly underground and outer scales develop protective pigmented papery skins. High potash enhances firmness and storage life; avoid erratic watering that causes split bulbs."),
                ("Maturity & Curing", 105, 120, "Tops soften and fall over at the neck (neck collapse) in over 50 percent of plants. Stop watering 10-15 days before lifting; cure bulbs in shade to ensure dry necks and tight skins."),
            ],
            "Tomato": [
                ("Nursery & Transplanting", 0, 25, "Vigorous seedlings from nursery trays are planted into staked field ridges with moist soil. Plants establish strong root balls and begin vegetative shoot growth; watch for cutworms and wilt."),
                ("Vegetative & Branching", 25, 45, "Stems thicken and lateral branches proliferate, forming a productive bush framework on stakes. Prune excess suckers and tie vines; monitor for tomato leaf curl virus and pinworm."),
                ("Flowering & Fruit Setting", 45, 70, "Yellow flower clusters bloom and vibrate to self-pollinate, setting clusters of green berries. Ideal temperatures of 20-28 C support fruit set; watch for blossom drop and fruit borer."),
                ("Fruit Development", 70, 90, "Green fruits swell to full mature size, accumulating sugars, acids, and vitamins in locular gel. Consistent soil moisture prevents fruit cracking and blossom end rot; inspect for late blight."),
                ("Maturity & Harvesting", 90, 110, "Fruits turn from breaker to red-ripe stage with high lycopene content and firm texture. Harvest in multiple pickings every 3-4 days based on market distance; handle carefully in crates."),
            ],
            "Potato": [
                ("Planting & Sprouting", 0, 15, "Certified seed tubers sprout in cool aerated ridge furrows, pushing shoots upward through soil. Emergence of primary stems establishes hill population; watch for black scurf and cutworms."),
                ("Vegetative Growth", 15, 35, "Stems and compound foliage expand rapidly into a lush canopy capturing maximum solar energy. Earth up ridges at 30 days to cover stolons; monitor lower leaves for early blight and aphids."),
                ("Tuber Initiation", 35, 55, "Subterranean stolon tips hook and swell into embryonic tuber initials as flowers open above ground. Cool night temperatures below 20 C favor tuberization; inspect for late blight lesions."),
                ("Tuber Bulking", 55, 75, "Tubers expand rapidly underground, accumulating starch and dry matter as primary carbohydrate sinks. Peak water and potassium requirement; keep tubers well covered from sunlight to avoid greening."),
                ("Tuber Maturity & Harvesting", 75, 90, "Vines senesce or are dehaulmed 10-12 days before digging to allow tuber skins to harden. Dig tubers carefully to avoid cuts; cure in cool shade before grading and cold storage."),
            ],
            "Turmeric": [
                ("Planting & Sprouting", 0, 40, "Seed rhizomes planted under heavy organic mulch sprout slowly and emerge above ridge soil. Warm moist soil encourages bud sprouting; watch for rhizome rot in poorly drained patches."),
                ("Vegetative & Tillering", 40, 110, "Broad lanceolate leaves and tillers multiply profusely, creating dense vegetative canopy clumps. Apply organic manure and nitrogen; monitor for leaf spot, leaf blotch, and shoot borers."),
                ("Rhizome Initiation", 110, 160, "Basal nodes begin swelling into primary and secondary finger rhizomes under the soil surface. Earth up loose soil around plants; provide steady potassium and watch for rhizome scales."),
                ("Rhizome Bulking", 160, 210, "Finger rhizomes thicken significantly, synthesizing high curcumin content and aromatic oils. Maintain optimal soil moisture without waterlogging; watch for bacterial wilt and leaf blight."),
                ("Maturity & Harvesting", 210, 240, "Leaves turn yellow, wither, and collapse onto the ground, signaling full rhizome maturity. Stop irrigation 15-20 days prior to digging; lift clumps carefully and cure rhizomes through boiling."),
            ],
            "Chilli": [
                ("Nursery & Transplanting", 0, 25, "Seedlings from pro-trays are transplanted into field ridges at 4-5 leaf stage in moist soil. Taproots establish and bushy erect shoots develop; watch for thrips causing upward leaf curl."),
                ("Vegetative Growth", 25, 55, "Dichotomous branching forms a sturdy spreading bush with prolific flower bud axils. Ridge cultivation and balanced NPK boost canopy size; watch for yellow mites and bacterial spot."),
                ("Flowering & Fruit Setting", 55, 85, "White star-shaped flowers blossom at branch forks and self-pollinate into slender green chillies. Warm sunny weather supports fruit set; monitor for blossom drop, fruit borer, and anthracnose."),
                ("Fruit Development", 85, 120, "Chillies lengthen, turn dark green and firm, accumulating capsaicin pungency throughout the pods. Regular light irrigation maintains fruit size; watch for fruit borer holes and die-back."),
                ("Maturity & Multiple Pickings", 120, 150, "Chillies turn deep red on plants and are harvested in multiple picking rounds every 10-14 days. Plucked red chillies are sun-dried on clean tarpaulins to 10 percent moisture."),
            ],
            "Ginger": [
                ("Planting & Emergence", 0, 35, "Rhizome bits with viable buds sprout through heavy green-leaf mulch in raised beds. Consistent warmth and moisture promote sprouting; watch for soft rot (Pythium) and shoot borers."),
                ("Vegetative & Tillering", 35, 95, "Slender pseudo-stems and narrow leaves multiply rapidly as clumps reach 8-12 tillers. Regular earthing up and green mulching conserve moisture; inspect for shoot borers and leaf spots."),
                ("Rhizome Initiation", 95, 145, "Underground fingers differentiate and branch out laterally from mother rhizomes in loose soil. High potassium supports finger formation; inspect for bacterial wilt and cover exposed fingers."),
                ("Rhizome Bulking", 145, 185, "Rhizome fingers expand in thickness, accumulating starch, fiber, and pungent gingerol oils. Light frequent irrigations maintain crumbly soil; watch for soft rot after heavy monsoon rains."),
                ("Maturity & Harvesting", 185, 210, "Foliage turns yellow and dries completely as rhizomes achieve maximum weight and fiber firmness. Clumps are carefully dug with forks, cleaned of roots, and dried in shade before marketing."),
            ],
        }

        stages_map = {}
        for crop_name, stages in stages_data.items():
            crop_obj = crops_map[crop_name]
            expected_names = {s_name for s_name, _, _, _ in stages}
            stmt_stale = select(CropStage).where(CropStage.crop_id == crop_obj.id, CropStage.stage_name.not_in(expected_names))
            stale_stages = (await db.execute(stmt_stale)).scalars().all()
            for st in stale_stages:
                await db.delete(st)
            await db.flush()

            for s_name, start, end, desc in stages:
                stmt = select(CropStage).where(CropStage.crop_id == crop_obj.id, CropStage.stage_name == s_name)
                st_obj = (await db.execute(stmt)).scalar_one_or_none()
                if not st_obj:
                    st_obj = CropStage(
                        crop_id=crop_obj.id,
                        stage_name=s_name,
                        start_day=start,
                        end_day=end,
                        stage_description=desc,
                        source=sample_source,
                    )
                    db.add(st_obj)
                    await db.flush()
                else:
                    st_obj.start_day = start
                    st_obj.end_day = end
                    st_obj.stage_description = desc
                    st_obj.source = sample_source
                    await db.flush()
                stages_map[(crop_name, s_name)] = st_obj

        print(f"  [OK] Crop Stages verified/seeded (all {len(stages_data)} crops with contiguous ICAR stages & descriptions).")

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
            ("Wheat", "Sowing", "Rotavator", -10, 5),
            ("Wheat", "Sowing", "Seed Drill", 0, 5),
            ("Wheat", "Tillering", "Sprayer", 25, 7),
            ("Wheat", "Grain Filling", "Harvester", 95, 7),
            ("Wheat", "Maturity", "Thresher", 110, 7),
            # Rice
            ("Rice", "Nursery", "Rotavator", -10, 5),
            ("Rice", "Transplanting & Establishment", "Seed Drill", 0, 5),
            ("Rice", "Tillering", "Sprayer", 30, 7),
            ("Rice", "Grain Filling", "Harvester", 110, 7),
            ("Rice", "Maturity & Harvest", "Thresher", 125, 7),
            # Maize
            ("Maize", "Sowing & Germination", "Rotavator", -10, 5),
            ("Maize", "Sowing & Germination", "Seed Drill", 0, 5),
            ("Maize", "Vegetative & Knee High", "Sprayer", 30, 7),
            ("Maize", "Grain Filling", "Harvester", 75, 7),
            ("Maize", "Maturity & Harvest", "Thresher", 95, 7),
            # Bajra
            ("Bajra", "Sowing & Seedling", "Rotavator", -8, 5),
            ("Bajra", "Sowing & Seedling", "Seed Drill", 0, 5),
            ("Bajra", "Tillering & Vegetative", "Sprayer", 25, 7),
            ("Bajra", "Grain Filling", "Harvester", 60, 7),
            ("Bajra", "Maturity & Harvest", "Thresher", 75, 7),
            # Jowar
            ("Jowar", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Jowar", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Jowar", "Vegetative Growth", "Sprayer", 35, 7),
            ("Jowar", "Grain Filling", "Harvester", 80, 7),
            ("Jowar", "Maturity & Harvest", "Thresher", 100, 7),
            # Tur/Arhar
            ("Tur/Arhar", "Sowing & Germination", "Rotavator", -10, 5),
            ("Tur/Arhar", "Sowing & Germination", "Seed Drill", 0, 5),
            ("Tur/Arhar", "Flowering & Pod Setting", "Sprayer", 95, 7),
            ("Tur/Arhar", "Pod Filling", "Harvester", 130, 7),
            ("Tur/Arhar", "Maturity & Harvest", "Thresher", 145, 7),
            # Gram (Chana)
            ("Gram (Chana)", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Gram (Chana)", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Gram (Chana)", "Flowering & Pod Initiation", "Sprayer", 45, 7),
            ("Gram (Chana)", "Pod Development & Filling", "Harvester", 75, 7),
            ("Gram (Chana)", "Maturity & Harvest", "Thresher", 90, 7),
            # Moong
            ("Moong", "Sowing & Emergence", "Rotavator", -7, 5),
            ("Moong", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Moong", "Vegetative Growth", "Sprayer", 15, 7),
            ("Moong", "Maturity & Harvesting", "Thresher", 60, 7),
            # Urad
            ("Urad", "Sowing & Emergence", "Rotavator", -7, 5),
            ("Urad", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Urad", "Vegetative Growth", "Sprayer", 18, 7),
            ("Urad", "Maturity & Harvesting", "Thresher", 65, 7),
            # Soybean
            ("Soybean", "Sowing & Germination", "Rotavator", -10, 5),
            ("Soybean", "Sowing & Germination", "Seed Drill", 0, 5),
            ("Soybean", "Flowering & Pod Initiation", "Sprayer", 45, 7),
            ("Soybean", "Pod Filling", "Harvester", 70, 7),
            ("Soybean", "Maturity & Harvest", "Thresher", 90, 7),
            # Groundnut
            ("Groundnut", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Groundnut", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Groundnut", "Vegetative Growth", "Sprayer", 25, 7),
            ("Groundnut", "Pod Development", "Tractor", 80, 7),
            ("Groundnut", "Maturity & Harvest", "Thresher", 105, 7),
            # Mustard
            ("Mustard", "Sowing & Emergence", "Rotavator", -10, 5),
            ("Mustard", "Sowing & Emergence", "Seed Drill", 0, 5),
            ("Mustard", "Flowering & Heading", "Sprayer", 50, 7),
            ("Mustard", "Siliqua & Pod Filling", "Harvester", 80, 7),
            ("Mustard", "Maturity & Harvest", "Thresher", 100, 7),
            # Cotton
            ("Cotton", "Sowing & Seedling", "Rotavator", -10, 5),
            ("Cotton", "Sowing & Seedling", "Seed Drill", 0, 5),
            ("Cotton", "Square Formation", "Sprayer", 55, 7),
            ("Cotton", "Boll Bursting & Harvest", "Harvester", 145, 7),
            # Sugarcane
            ("Sugarcane", "Planting & Germination", "Rotavator", -10, 5),
            ("Sugarcane", "Planting & Germination", "Seed Drill", 0, 5),
            ("Sugarcane", "Formative Tillering", "Sprayer", 55, 7),
            ("Sugarcane", "Grand Growth", "Tractor", 150, 7),
            ("Sugarcane", "Harvest & Maturation", "Harvester", 330, 10),
            # Onion
            ("Onion", "Nursery & Transplanting", "Rotavator", -10, 5),
            ("Onion", "Vegetative Growth", "Tractor", 40, 7),
            ("Onion", "Bulb Initiation", "Sprayer", 70, 7),
            ("Onion", "Maturity & Curing", "Tractor", 115, 7),
            # Tomato
            ("Tomato", "Nursery & Transplanting", "Rotavator", -10, 5),
            ("Tomato", "Vegetative & Branching", "Sprayer", 35, 7),
            ("Tomato", "Flowering & Fruit Setting", "Sprayer", 55, 7),
            ("Tomato", "Maturity & Harvesting", "Tractor", 95, 7),
            # Potato
            ("Potato", "Planting & Sprouting", "Rotavator", -10, 5),
            ("Potato", "Planting & Sprouting", "Seed Drill", 0, 5),
            ("Potato", "Vegetative Growth", "Sprayer", 25, 7),
            ("Potato", "Tuber Maturity & Harvesting", "Tractor", 85, 7),
            # Turmeric
            ("Turmeric", "Planting & Sprouting", "Rotavator", -10, 5),
            ("Turmeric", "Vegetative & Tillering", "Tractor", 60, 7),
            ("Turmeric", "Rhizome Initiation", "Sprayer", 125, 7),
            ("Turmeric", "Maturity & Harvesting", "Tractor", 220, 7),
            # Chilli
            ("Chilli", "Nursery & Transplanting", "Rotavator", -10, 5),
            ("Chilli", "Vegetative Growth", "Sprayer", 35, 7),
            ("Chilli", "Flowering & Fruit Setting", "Sprayer", 65, 7),
            ("Chilli", "Maturity & Multiple Pickings", "Tractor", 125, 7),
            # Ginger
            ("Ginger", "Planting & Emergence", "Rotavator", -10, 5),
            ("Ginger", "Vegetative & Tillering", "Tractor", 55, 7),
            ("Ginger", "Rhizome Initiation", "Sprayer", 110, 7),
            ("Ginger", "Maturity & Harvesting", "Tractor", 195, 7),
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
            {"crop": "Wheat", "stage": "Tillering", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Tillering"}, "guidance": "Apply 60 kg/acre Urea during Tillering stage to promote strong productive tillers.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Wheat", "stage": "Tillering", "nutrient": "Zinc", "condition": {"nutrient": "zinc", "level": ["low"], "stage": "Tillering"}, "guidance": "Foliar spray of 0.5% Zinc Sulphate with 0.25% Lime at tillering to prevent zinc deficiency chlorosis.", "category": "Micro-Nutrient", "source": sample_source},
            # Rice
            {"crop": "Rice", "stage": "Tillering", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Tillering"}, "guidance": "Apply 40 kg/acre Single Super Phosphate (SSP) at tillering.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Rice", "stage": "Flowering & Heading", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Heading"}, "guidance": "Top dress 25 kg/acre Muriate of Potash (MOP) during heading for healthy panicle filling.", "category": "Fertilizer", "source": sample_source},
            # Cotton
            {"crop": "Cotton", "stage": "Sowing & Seedling", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Sowing & Seedling"}, "guidance": "Review nitrogen management during the seedling stage.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Cotton", "stage": "Square Formation", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Square Formation"}, "guidance": "Review phosphorus management before square formation to prevent premature bud drop.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Cotton", "stage": "Peak Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Peak Flowering"}, "guidance": "Review potassium management during peak flowering to support expanding bolls.", "category": "Fertilizer", "source": sample_source},
            # Soybean
            {"crop": "Soybean", "stage": "Vegetative Growth", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Review phosphorus management during early growth to boost Rhizobium nodulation.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Soybean", "stage": "Flowering & Pod Initiation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Initiation"}, "guidance": "Review potassium management during flowering for maximum pod retention.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Soybean", "stage": "Pod Filling", "nutrient": "Organic Carbon", "condition": {"nutrient": "organic_carbon", "level": ["low"], "stage": "Pod Filling"}, "guidance": "Review organic matter management during pod filling.", "category": "Organic", "source": sample_source},
            # Sugarcane
            {"crop": "Sugarcane", "stage": "Planting & Germination", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Planting & Germination"}, "guidance": "Review nitrogen management during germination.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Sugarcane", "stage": "Formative Tillering", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Formative Tillering"}, "guidance": "Review phosphorus management during tillering to build thick millable canes.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Sugarcane", "stage": "Grand Growth", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Grand Growth"}, "guidance": "Review potassium management during grand growth to support stalk elongation.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Sugarcane", "stage": "Ripening", "nutrient": "Organic Carbon", "condition": {"nutrient": "organic_carbon", "level": ["low"], "stage": "Ripening"}, "guidance": "Review organic matter management before harvest.", "category": "Organic", "source": sample_source},
            # Maize
            {"crop": "Maize", "stage": "Vegetative & Knee High", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative & Knee High"}, "guidance": "Apply side-dress nitrogen fertilizer during knee-high stage.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Maize", "stage": "Tasseling & Silking", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Tasseling & Silking"}, "guidance": "Apply potassium to support tasseling and grain filling.", "category": "Fertilizer", "source": sample_source},
            # Bajra
            {"crop": "Bajra", "stage": "Tillering & Vegetative", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Tillering & Vegetative"}, "guidance": "Top dress nitrogen at 3-4 weeks after sowing during tillering.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Bajra", "stage": "Booting & Flowering", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Booting & Flowering"}, "guidance": "Ensure adequate phosphorus availability during earhead emergence.", "category": "Fertilizer", "source": sample_source},
            # Jowar
            {"crop": "Jowar", "stage": "Vegetative Growth", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Split application of nitrogen during peak vegetative stage.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Jowar", "stage": "Booting & Flowering", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Booting & Flowering"}, "guidance": "Apply potash at boot stage for strong stalk and earhead filling.", "category": "Fertilizer", "source": sample_source},
            # Tur/Arhar
            {"crop": "Tur/Arhar", "stage": "Branching & Vegetative", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Branching & Vegetative"}, "guidance": "Apply phosphorus and Rhizobium biofertilizer to promote root nodulation.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Tur/Arhar", "stage": "Flowering & Pod Setting", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Setting"}, "guidance": "Apply foliar potassium spray to minimize flower drop and enhance pod fill.", "category": "Fertilizer", "source": sample_source},
            # Gram (Chana)
            {"crop": "Gram (Chana)", "stage": "Branching & Vegetative", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Branching & Vegetative"}, "guidance": "Apply Single Super Phosphate (SSP) at branching to enhance root nodules.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Gram (Chana)", "stage": "Flowering & Pod Initiation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Initiation"}, "guidance": "Apply 2% DAP or Potassium foliar spray during pod formation.", "category": "Fertilizer", "source": sample_source},
            # Moong
            {"crop": "Moong", "stage": "Vegetative Growth", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Ensure adequate phosphorus and sulfur for nodule development.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Moong", "stage": "Flowering & Pod Formation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Formation"}, "guidance": "Foliar nutrient spray to prevent flower drop during early pod set.", "category": "Fertilizer", "source": sample_source},
            # Urad
            {"crop": "Urad", "stage": "Vegetative Growth", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Basal phosphorus application promotes rapid root growth and nodulation.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Urad", "stage": "Flowering & Pod Initiation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Flowering & Pod Initiation"}, "guidance": "Apply foliar potassium spray at pod setting for uniform grain fill.", "category": "Fertilizer", "source": sample_source},
            # Groundnut
            {"crop": "Groundnut", "stage": "Flowering & Pegging", "nutrient": "Calcium", "condition": {"nutrient": "calcium", "level": ["low"], "stage": "Flowering & Pegging"}, "guidance": "Apply gypsum (200 kg/acre) during pegging for pod filling and shell hardening.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Groundnut", "stage": "Pod Development", "nutrient": "Phosphorus", "condition": {"nutrient": "phosphorus", "level": ["low"], "stage": "Pod Development"}, "guidance": "Maintain balanced soil phosphorus to support continuous peg development.", "category": "Fertilizer", "source": sample_source},
            # Mustard
            {"crop": "Mustard", "stage": "Vegetative & Rosette", "nutrient": "Sulfur", "condition": {"nutrient": "sulfur", "level": ["low"], "stage": "Vegetative & Rosette"}, "guidance": "Apply sulfur (20 kg/acre) to boost oil content and vegetative vigor.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Mustard", "stage": "Flowering & Heading", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Flowering & Heading"}, "guidance": "Top dress nitrogen with first flowering irrigation.", "category": "Fertilizer", "source": sample_source},
            # Onion
            {"crop": "Onion", "stage": "Vegetative Growth", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Apply split dose of nitrogen 30 days after transplanting.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Onion", "stage": "Bulb Initiation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Bulb Initiation"}, "guidance": "Apply Sulfate of Potash (SOP) to boost bulb weight and storage quality.", "category": "Fertilizer", "source": sample_source},
            # Tomato
            {"crop": "Tomato", "stage": "Vegetative & Branching", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative & Branching"}, "guidance": "Apply balanced NPK fertigation during vegetative branching.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Tomato", "stage": "Flowering & Fruit Setting", "nutrient": "Calcium", "condition": {"nutrient": "calcium", "level": ["low"], "stage": "Flowering & Fruit Setting"}, "guidance": "Foliar spray of Calcium Nitrate to prevent blossom end rot.", "category": "Micro-Nutrient", "source": sample_source},
            # Potato
            {"crop": "Potato", "stage": "Vegetative Growth", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Top dress nitrogen during first earthing up at 30 days.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Potato", "stage": "Tuber Initiation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Tuber Initiation"}, "guidance": "Apply MOP or SOP during tuber bulking to maximize tuber size.", "category": "Fertilizer", "source": sample_source},
            # Turmeric
            {"crop": "Turmeric", "stage": "Vegetative & Tillering", "nutrient": "Organic Carbon", "condition": {"nutrient": "organic_carbon", "level": ["low"], "stage": "Vegetative & Tillering"}, "guidance": "Apply well-decomposed FYM/compost and neem cake at tillering.", "category": "Organic", "source": sample_source},
            {"crop": "Turmeric", "stage": "Rhizome Initiation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Rhizome Initiation"}, "guidance": "Apply potassium and micronutrients to maximize rhizome size and curcumin.", "category": "Fertilizer", "source": sample_source},
            # Chilli
            {"crop": "Chilli", "stage": "Vegetative Growth", "nutrient": "Nitrogen", "condition": {"nutrient": "nitrogen", "level": ["low"], "stage": "Vegetative Growth"}, "guidance": "Apply nitrogen fertigation at 3-4 weeks after transplanting.", "category": "Fertilizer", "source": sample_source},
            {"crop": "Chilli", "stage": "Flowering & Fruit Setting", "nutrient": "Boron", "condition": {"nutrient": "boron", "level": ["low"], "stage": "Flowering & Fruit Setting"}, "guidance": "Foliar spray of Boron (0.1%) to reduce flower dropping and enhance fruit set.", "category": "Micro-Nutrient", "source": sample_source},
            # Ginger
            {"crop": "Ginger", "stage": "Vegetative & Tillering", "nutrient": "Organic Carbon", "condition": {"nutrient": "organic_carbon", "level": ["low"], "stage": "Vegetative & Tillering"}, "guidance": "Apply green manure mulch and compost at first earthing up.", "category": "Organic", "source": sample_source},
            {"crop": "Ginger", "stage": "Rhizome Initiation", "nutrient": "Potassium", "condition": {"nutrient": "potassium", "level": ["low"], "stage": "Rhizome Initiation"}, "guidance": "Apply potash at rhizome development for optimal yield and fiber quality.", "category": "Fertilizer", "source": sample_source},
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
        # Ensure demo farmer has multiple farms with distinct crops (Wheat, Rice, Cotton)
        demo_farmer = farmer_users[0]
        demo_crops = [
            ("Wheat", 30, "Loam", "Tillering", "Drip"),
            ("Rice", 45, "Clay Loam", "Tillering", "Canal"),
            ("Cotton", 60, "Black Cotton", "Square Formation", "Drip"),
        ]
        for c_name, days_ago, stype, stage_name, irr_type in demo_crops:
            crop_obj = crops_map.get(c_name)
            if not crop_obj:
                continue
            stmt = select(Farm).where(Farm.farmer_id == demo_farmer.id, Farm.crop_id == crop_obj.id)
            existing_f = (await db.execute(stmt)).scalar_one_or_none()
            if not existing_f:
                sow_date = date.today() - timedelta(days=days_ago)
                f_obj = Farm(
                    farmer_id=demo_farmer.id,
                    crop_id=crop_obj.id,
                    sowing_date=sow_date,
                    area_acres=2.5,
                    soil_type=stype,
                    current_stage=stage_name,
                    irrigation_type=irr_type,
                )
                db.add(f_obj)
                await db.flush()
                st = SoilTest(
                    farm_id=f_obj.id,
                    ph=6.8,
                    nitrogen=240.0,
                    phosphorus=18.0,
                    potassium=190.0,
                    organic_carbon=0.55,
                    tested_on=date.today() - timedelta(days=20),
                )
                db.add(st)
                await db.flush()
                farm_ids.append(f_obj.id)
            else:
                farm_ids.append(existing_f.id)

        for farmer in farmer_users[1:]:
            stmt = select(Farm).where(Farm.farmer_id == farmer.id).order_by(Farm.id)
            existing_farm = (await db.execute(stmt)).scalars().first()
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

        # 10. Seed Government Schemes
        schemes_data = [
            {
                "name": "PM-KISAN",
                "name_hi": "पीएम-किसान",
                "name_mr": "पीएम-किसान",
                "level": "central",
                "department": "Ministry of Agriculture & Farmers Welfare",
                "short_description": "Direct income support of ₹6,000 per year to farmer families in three equal installments.",
                "eligibility_text": "All landholding farmer families with cultivable land are eligible. Institutional landholders are not eligible.",
                "benefits_text": "₹6,000 per year per farmer family in three equal installments of ₹2,000 each.",
                "required_documents": ["Aadhaar Card", "Land Records", "Bank Account linked with Aadhaar", "Mobile Number"],
                "application_process_text": "Register online through PM-KISAN portal or visit nearest CSC center. Provide Aadhaar, land details, and bank account information.",
                "official_link": "https://pmkisan.gov.in",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": [],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "PM Fasal Bima Yojana",
                "name_hi": "पीएम फसल बीमा योजना",
                "name_mr": "पीएम फसल बीमा योजना",
                "level": "central",
                "department": "Ministry of Agriculture & Farmers Welfare",
                "short_description": "Crop insurance scheme providing coverage against crop failure due to natural calamities, pests, and diseases.",
                "eligibility_text": "All farmers growing notified crops in notified areas are eligible. Loanee and non-loanee farmers both covered.",
                "benefits_text": "Premium subsidy up to 50% for food crops and 40% for oilseeds. Sum insured based on crop yield and historical data.",
                "required_documents": ["Aadhaar Card", "Land Records", "Bank Account", "Crop Details", "Khasra Number"],
                "application_process_text": "Apply through designated banks or insurance companies. Provide land documents, crop details, and bank account. Premium deducted from loan account for loanee farmers.",
                "official_link": "https://pmfby.gov.in",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": [],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "Soil Health Card Scheme",
                "name_hi": "स्वास्थ्य कार्ड योजना",
                "name_mr": "माती आरोग्य कार्ड योजना",
                "level": "central",
                "department": "Ministry of Agriculture & Farmers Welfare",
                "short_description": "Provides soil health cards to farmers with soil nutrient status and recommendations for balanced fertilizer use.",
                "eligibility_text": "All farmers are eligible. No specific restrictions.",
                "benefits_text": "Free soil testing and soil health card with nutrient status and fertilizer recommendations every 3 years.",
                "required_documents": ["Aadhaar Card", "Land Records", "Farm Location Details"],
                "application_process_text": "Visit nearest soil testing laboratory or agriculture department office. Submit soil sample along with land documents.",
                "official_link": "https://soilhealth.dac.gov.in",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": [],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "Kisan Credit Card (KCC)",
                "name_hi": "किसान क्रेडिट कार्ड",
                "name_mr": "किसान क्रेडिट कार्ड",
                "level": "central",
                "department": "Ministry of Agriculture & Farmers Welfare",
                "short_description": "Credit card scheme for farmers to meet their cultivation needs and other expenses.",
                "eligibility_text": "All farmers including tenant farmers, sharecroppers, and oral lessees are eligible.",
                "benefits_text": "Credit limit up to ₹3 lakh with interest subvention of 2% per annum on timely repayment. Credit for cultivation and post-harvest expenses.",
                "required_documents": ["Aadhaar Card", "Land Records or Tenancy Proof", "Bank Account", "Passport Size Photo", "Income Proof"],
                "application_process_text": "Apply at nearest bank branch. Submit land documents, identity proof, bank account details, and photograph.",
                "official_link": "https://www.mof.gov.in",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": [],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "PM Krishi Sinchayee Yojana (PMKSY)",
                "name_hi": "पीएम कृषि सिंचाई योजना",
                "name_mr": "पीएम कृषी सिंचन योजना",
                "level": "central",
                "department": "Ministry of Agriculture & Farmers Welfare",
                "short_description": "Irrigation scheme promoting end-to-end irrigation solutions including water source, distribution, and field application.",
                "eligibility_text": "Farmers with irrigable land are eligible. State governments can also apply for infrastructure projects.",
                "benefits_text": "Subsidy up to 90% for micro-irrigation (drip/sprinkler) for small farmers. Financial assistance for water conservation projects.",
                "required_documents": ["Aadhaar Card", "Land Records", "Bank Account", "Farm Map", "Water Source Details"],
                "application_process_text": "Apply through state agriculture department or PMKSY portal. Submit land documents, water source details, and project proposal.",
                "official_link": "https://pmksy.gov.in",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": [],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "Namo Shetkari Mahasanman Nidhi Yojana",
                "name_hi": "नमो शेतकरी महासम्मान निधि योजना",
                "name_mr": "नमो शेतकरी महासन्मान निधी योजना",
                "level": "state",
                "department": "Government of Maharashtra, Agriculture Department",
                "short_description": "Maharashtra income-support scheme for eligible farmers; confirm current eligibility and payment rules on the official portal.",
                "eligibility_text": "Eligibility and exclusions are governed by current Maharashtra government guidelines. Check the official portal for the latest criteria.",
                "benefits_text": "Financial support is subject to current scheme rules, budget, and beneficiary verification. Confirm amounts and payment schedules on the official portal.",
                "required_documents": ["Aadhaar Card", "Land Records", "Bank Account Details", "PM-KISAN Beneficiary Details"],
                "application_process_text": "Check beneficiary status and current instructions through the Maharashtra Agriculture Department or the linked official scheme portal.",
                "official_link": "https://krishi.maharashtra.gov.in/",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": ["Maharashtra"],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "Maharashtra State Scheme - Jalyukt Shivar Abhiyan",
                "name_hi": "महाराष्ट्र राज्य योजना - जलयुक्त शिवार अभियान",
                "name_mr": "महाराष्ट्र राज्य योजना - जलयुक्त शिवार अभियान",
                "level": "state",
                "department": "Maharashtra Water Resources Department",
                "short_description": "Water conservation scheme to make Maharashtra drought-free through watershed development and water conservation works.",
                "eligibility_text": "Farmers and village communities in Maharashtra are eligible. Priority given to drought-prone areas.",
                "benefits_text": "Free construction of farm ponds, check dams, and water conservation structures. 100% grant for community projects.",
                "required_documents": ["Aadhaar Card", "Land Records", "7/12 Extract", "Village Resolution", "Bank Account"],
                "application_process_text": "Apply through Gram Panchayat or Water Conservation Department. Submit land documents, village resolution, and project proposal.",
                "official_link": "https://jalyuktshivar.maharashtra.gov.in",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": ["Maharashtra"],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "National Food Security Mission (NFSM)",
                "name_hi": "राष्ट्रीय खाद्य सुरक्षा मिशन",
                "name_mr": "राष्ट्रीय अन्न सुरक्षा मिशन",
                "level": "central",
                "department": "Ministry of Agriculture & Farmers Welfare",
                "short_description": "Mission to increase production of rice, wheat, pulses, and coarse cereals through area expansion and productivity enhancement.",
                "eligibility_text": "Farmers cultivating rice, wheat, pulses, millets, and barley in identified districts are eligible.",
                "benefits_text": "Subsidized seeds, fertilizers, and machinery. Financial assistance for cluster demonstrations and seed distribution.",
                "required_documents": ["Aadhaar Card", "Land Records", "Bank Account", "Crop Details"],
                "application_process_text": "Apply through district agriculture office. Submit land documents, crop details, and bank account.",
                "official_link": "https://nfsm.gov.in",
                "deadline": None,
                "status": "active",
                "crops": ["Wheat", "Rice", "Maize", "Bajra", "Jowar", "Tur/Arhar", "Gram (Chana)", "Moong", "Urad"],
                "states": [],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "Sub-Mission on Agricultural Mechanization (SMAM)",
                "name_hi": "कृषि यांत्रिकीकरण पर उप-मिशन",
                "name_mr": "कृषी यंत्रीकरणावर उप-मिशन",
                "level": "central",
                "department": "Ministry of Agriculture & Farmers Welfare",
                "short_description": "Promotes agricultural mechanization by providing subsidy on purchase of farm machinery and equipment.",
                "eligibility_text": "Individual farmers, farmer groups, cooperatives, and institutions are eligible.",
                "benefits_text": "Subsidy up to 50% on purchase of tractors, harvesters, and other farm machinery. Higher subsidy for small and marginal farmers.",
                "required_documents": ["Aadhaar Card", "Land Records", "Bank Account", "Quotation of Machinery", "Caste Certificate (if applicable)"],
                "application_process_text": "Apply through state agriculture department. Submit quotation, land documents, bank details, and identity proof.",
                "official_link": "https://agrimachinery.nic.in",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": [],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            },
            {
                "name": "Maharashtra Agriculture Business School (MABS)",
                "name_hi": "महाराष्ट्र कृषि व्यवसाय विद्यालय",
                "name_mr": "महाराष्ट्र कृषी व्यवसाय विद्यालय",
                "level": "state",
                "department": "Government of Maharashtra, Agriculture Department",
                "short_description": "Training and capacity building program for farmers to enhance agricultural productivity and income through modern practices.",
                "eligibility_text": "Farmers, farmer groups, and rural youth in Maharashtra are eligible. Priority given to progressive farmers.",
                "benefits_text": "Free training on modern farming techniques, post-harvest management, value addition, and market linkage. Exposure visits and field demonstrations.",
                "required_documents": ["Aadhaar Card", "Land Records", "Bank Account", "Passport Size Photo"],
                "application_process_text": "Apply through nearest Agriculture Department office or Krishi Vigyan Kendra. Submit documents and attend training program.",
                "official_link": "https://krishi.maharashtra.gov.in",
                "deadline": None,
                "status": "active",
                "crops": [],
                "states": ["Maharashtra"],
                "last_verified_on": datetime(2024, 10, 1),
                "source": "Verify current details on official portal before relying on this"
            }
        ]

        localized_scheme_summaries = {
            "PM-KISAN": (
                "पात्र किसान परिवारों को आय सहायता देने वाली केंद्र सरकार की योजना। वर्तमान पात्रता और भुगतान की पुष्टि आधिकारिक पोर्टल पर करें।",
                "पात्र शेतकरी कुटुंबांना उत्पन्न सहाय्य देणारी केंद्र सरकारची योजना. सध्याची पात्रता आणि देयकांची अधिकृत पोर्टलवर खात्री करा.",
            ),
            "PM Fasal Bima Yojana": (
                "अधिसूचित फसलों के लिए फसल बीमा योजना। कवरेज, प्रीमियम और आवेदन की समय-सीमा हर मौसम में बदल सकती है।",
                "अधिसूचित पिकांसाठी पीक विमा योजना. संरक्षण, विमा हप्ता आणि अर्जाची मुदत प्रत्येक हंगामात बदलू शकते.",
            ),
            "Soil Health Card Scheme": (
                "मिट्टी की जांच और पोषक तत्वों की जानकारी के लिए किसान-केंद्रित योजना। उपलब्धता के लिए स्थानीय कृषि विभाग से संपर्क करें।",
                "माती परीक्षण आणि पोषक घटकांची माहिती देणारी शेतकरी-केंद्रित योजना. उपलब्धतेसाठी स्थानिक कृषी विभागाशी संपर्क साधा.",
            ),
            "Kisan Credit Card (KCC)": (
                "खेती और संबंधित जरूरतों के लिए संस्थागत ऋण सुविधा। पात्रता और ब्याज की शर्तें बैंक तथा वर्तमान दिशानिर्देशों पर निर्भर हैं।",
                "शेती आणि संबंधित गरजांसाठी संस्थात्मक कर्ज सुविधा. पात्रता आणि व्याजाच्या अटी बँक व सध्याच्या मार्गदर्शक तत्त्वांवर अवलंबून आहेत.",
            ),
            "PM Krishi Sinchayee Yojana (PMKSY)": (
                "सिंचाई, जल दक्षता और जल संरक्षण को बढ़ावा देने वाली योजना। सहायता संबंधित घटक और राज्य के नियमों के अनुसार मिलती है।",
                "सिंचन, जलकार्यक्षमता आणि जलसंधारणाला प्रोत्साहन देणारी योजना. मदत संबंधित घटक आणि राज्याच्या नियमांनुसार मिळते.",
            ),
            "Namo Shetkari Mahasanman Nidhi Yojana": (
                "महाराष्ट्र के पात्र किसानों के लिए आय सहायता योजना। वर्तमान पात्रता और भुगतान नियम आधिकारिक पोर्टल पर जांचें।",
                "महाराष्ट्रातील पात्र शेतकऱ्यांसाठी उत्पन्न सहाय्य योजना. सध्याची पात्रता आणि देयकांचे नियम अधिकृत पोर्टलवर तपासा.",
            ),
            "Maharashtra State Scheme - Jalyukt Shivar Abhiyan": (
                "महाराष्ट्र में जल संरक्षण और जल उपलब्धता बढ़ाने का अभियान। गांवों और कार्यों की वर्तमान पात्रता आधिकारिक स्रोत से जांचें।",
                "महाराष्ट्रातील जलसंधारण आणि पाणी उपलब्धता वाढवण्याचा उपक्रम. गावांची आणि कामांची सध्याची पात्रता अधिकृत स्रोतावर तपासा.",
            ),
            "National Food Security Mission (NFSM)": (
                "चयनित क्षेत्रों में प्रमुख खाद्यान्न फसलों की उत्पादकता बढ़ाने का मिशन। फसल और जिले की पात्रता की पुष्टि करें।",
                "निवडक भागांमध्ये प्रमुख अन्नधान्य पिकांची उत्पादकता वाढवणारे अभियान. पीक आणि जिल्ह्याची पात्रता तपासा.",
            ),
            "Sub-Mission on Agricultural Mechanization (SMAM)": (
                "कृषि यंत्रीकरण को बढ़ावा देने वाला कार्यक्रम। मशीनों, सहायता और आवेदन की शर्तें राज्य के अनुसार बदलती हैं।",
                "कृषी यांत्रिकीकरणाला प्रोत्साहन देणारा कार्यक्रम. यंत्रे, सहाय्य आणि अर्जाच्या अटी राज्यानुसार बदलतात.",
            ),
            "Maharashtra Agriculture Business School (MABS)": (
                "महाराष्ट्र राज्य में कृषि व्यवसाय और आधुनिक कृषि प्रशिक्षण के लिए किसान क्षमता निर्माण योजना। आवेदन और शेड्यूल स्थानीय कृषि विभाग से सत्यापित करें।",
                "महाराष्ट्र राज्यात कृषी व्यवसाय आणि आधुनिक कृषी प्रशिक्षणासाठी शेतकरी क्षमता निर्माण योजना. अर्ज आणि वेळापत्रक स्थानिक कृषी विभागातून सत्यापित करा.",
            ),
        }

        for scheme_data in schemes_data:
            scheme_data["short_description_hi"], scheme_data["short_description_mr"] = localized_scheme_summaries[
                scheme_data["name"]
            ]
            scheme_data["last_verified_on"] = datetime(2026, 10, 2)
            stmt = select(Scheme).where(Scheme.name == scheme_data["name"])
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if not existing:
                existing = Scheme(**scheme_data)
                db.add(existing)
                await db.flush()
            else:
                for key, value in scheme_data.items():
                    setattr(existing, key, value)
                await db.flush()

        print(f"  [OK] {len(schemes_data)} Government Schemes verified/seeded.")

        # 11. Seed Sample Booking Group & Members (Testing Group Constraint)
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
                    stmt_farm = select(Farm).where(Farm.farmer_id == f_user.id).order_by(Farm.id)
                    f_farm = (await db.execute(stmt_farm)).scalars().first()
                    if not f_farm:
                        continue

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
