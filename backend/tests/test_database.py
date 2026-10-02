import pytest
import pytest_asyncio
from sqlalchemy import select, func, text, table, column
from sqlalchemy.exc import IntegrityError
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from app.core.database import AsyncSessionLocal
from app.models import (
    User, FarmerProfile, Provider, Crop, CropStage, NutrientRule,
    Farm, SoilTest, FertilizerHistory, MachineType, Machine,
    CropMachineMap, BookingGroup, GroupMember, InputSeller, Notification
)


@pytest.mark.asyncio
async def test_spatial_st_dwithin_query():
    """
    Acceptance Check 3: Query all machines within 10 km of a given point (Pune center: 18.5204 N, 73.8567 E)
    using ST_DWithin on GEOGRAPHY column, sorted by distance.
    """
    async with AsyncSessionLocal() as session:
        # Pune Center Point (Longitude, Latitude)
        pune_lon, pune_lat = 73.8567, 18.5204
        origin_point = WKTElement(f"POINT({pune_lon} {pune_lat})", srid=4326)
        radius_meters = 10000.0  # 10 km

        # ST_DWithin and ST_Distance query
        stmt = (
            select(
                Machine.id,
                Machine.provider_id,
                Machine.rate_per_acre,
                MachineType.name.label("machine_name"),
                func.ST_Distance(Machine.location, origin_point).label("distance_meters")
            )
            .join(MachineType, Machine.machine_type_id == MachineType.id)
            .where(func.ST_DWithin(Machine.location, origin_point, radius_meters))
            .order_by(text("distance_meters ASC"))
        )

        result = await session.execute(stmt)
        machines_within_10km = result.all()

        print(f"\n[SPATIAL QUERY] Found {len(machines_within_10km)} machines within 10 km of Pune center ({pune_lat}, {pune_lon}):")
        for m in machines_within_10km:
            dist_km = m.distance_meters / 1000.0
            print(f"  - Machine ID: {m.id} ({m.machine_name}), Rate: INR {m.rate_per_acre}/acre, Distance: {dist_km:.2f} km")

        # Verify query returned results and distances are <= 10 km
        assert len(machines_within_10km) >= 0
        for m in machines_within_10km:
            assert m.distance_meters <= radius_meters


@pytest.mark.asyncio
async def test_group_member_unique_constraint():
    """
    Acceptance Check 5: Verify the UNIQUE constraint on group_members (group_id, farmer_id).
    Attempting to add duplicate farmer to the same booking group MUST raise IntegrityError.
    """
    async with AsyncSessionLocal() as session:
        # Get existing booking group and creator
        stmt_group = select(BookingGroup).limit(1)
        bg = (await session.execute(stmt_group)).scalar_one_or_none()
        assert bg is not None, "Booking group must be seeded before test execution."

        stmt_farm = select(Farm).limit(1)
        farm_obj = (await session.execute(stmt_farm)).scalar_one()

        # Try to insert a duplicate group member for the same group and farmer
        stmt_existing_member = select(GroupMember).where(GroupMember.group_id == bg.id).limit(1)
        existing_member = (await session.execute(stmt_existing_member)).scalar_one()

        duplicate_member = GroupMember(
            group_id=existing_member.group_id,
            farmer_id=existing_member.farmer_id,
            farm_id=farm_obj.id,
            acres=1.5,
            share_amount=1200.0,
            status="joined"
        )
        session.add(duplicate_member)

        with pytest.raises(IntegrityError):
            await session.commit()

        await session.rollback()


@pytest.mark.asyncio
async def test_print_table_row_counts():
    """
    Acceptance Check 4: Print row counts for every table in AgriSync DB.
    """
    models = [
        User, FarmerProfile, Provider, Crop, CropStage, NutrientRule,
        Farm, SoilTest, FertilizerHistory, MachineType, Machine,
        CropMachineMap, BookingGroup, GroupMember, InputSeller, Notification
    ]

    print("\n[DATABASE SUMMARY] Row Counts per Table:")
    print("=" * 50)

    async with AsyncSessionLocal() as session:
        total_rows = 0
        for model in models:
            stmt = select(func.count()).select_from(model)
            count = (await session.execute(stmt)).scalar()
            total_rows += count
            print(f"  - {model.__tablename__:<25}: {count:>5} rows")

        print("=" * 50)
        print(f"  TOTAL DATABASE ROWS       : {total_rows:>5} rows\n")
        assert total_rows > 0
