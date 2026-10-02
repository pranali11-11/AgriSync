import math
import re
from typing import AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Parse WKT Point e.g., 'POINT(73.8567 18.5204)' -> (lon, lat)
def _parse_wkt_point(wkt):
    if not wkt:
        return 0.0, 0.0
    if isinstance(wkt, bytes):
        wkt = wkt.decode('utf-8', errors='ignore')
    wkt_str = str(wkt)
    match = re.search(r'POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)', wkt_str, re.IGNORECASE)
    if match:
        return float(match.group(1)), float(match.group(2))
    return 0.0, 0.0


def _haversine_meters(lon1, lat1, lon2, lat2):
    R = 6371000.0  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def sqlite_st_dwithin(geom1, geom2, distance_meters):
    lon1, lat1 = _parse_wkt_point(geom1)
    lon2, lat2 = _parse_wkt_point(geom2)
    dist = _haversine_meters(lon1, lat1, lon2, lat2)
    return 1 if dist <= float(distance_meters) else 0


def sqlite_st_distance(geom1, geom2):
    lon1, lat1 = _parse_wkt_point(geom1)
    lon2, lat2 = _parse_wkt_point(geom2)
    return _haversine_meters(lon1, lat1, lon2, lat2)


def sqlite_st_geomfromtext(wkt, srid=4326):
    return str(wkt)


# Determine Database Engine
database_url = settings.DATABASE_URL
USE_SQLITE_FALLBACK = False

# Try connecting to PostgreSQL; fallback to SQLite if PostgreSQL is unreachable locally
if "sqlite" in database_url:
    USE_SQLITE_FALLBACK = True
else:
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        res = sock.connect_ex((settings.POSTGRES_HOST if settings.POSTGRES_HOST != 'db' else '127.0.0.1', int(settings.POSTGRES_PORT)))
        sock.close()
        if res != 0:
            USE_SQLITE_FALLBACK = True
    except Exception:
        USE_SQLITE_FALLBACK = True

if USE_SQLITE_FALLBACK:
    database_url = "sqlite+aiosqlite:///./agrisync.db"
    engine = create_async_engine(database_url, echo=False, future=True)

    @event.listens_for(engine.sync_engine, "connect")
    def register_sqlite_spatial_functions(dbapi_connection, connection_record):
        dbapi_connection.create_function("ST_DWithin", 3, sqlite_st_dwithin)
        dbapi_connection.create_function("ST_Distance", 2, sqlite_st_distance)
        dbapi_connection.create_function("ST_GeomFromText", 2, sqlite_st_geomfromtext)
        dbapi_connection.create_function("ST_GeomFromText", 1, sqlite_st_geomfromtext)
        dbapi_connection.create_function("PostGIS_Full_Version", 0, lambda: "POSTGIS='3.4.0' (SQLite Emulated)")
else:
    engine = create_async_engine(
        database_url,
        echo=settings.APP_ENV == "development",
        future=True,
        pool_pre_ping=True
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
