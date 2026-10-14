"""
Tests for POST /auth/request-otp, POST /auth/verify-otp, and profile name validation
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.deps import get_redis
from app.api.v1.endpoints import auth as auth_endpoint
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_jwt_token
from app.models.user import Provider, User


def test_local_vite_ports_are_allowed_for_cors():
    assert "http://localhost:4173" in settings.CORS_ORIGINS
    assert "http://127.0.0.1:4173" in settings.CORS_ORIGINS
    assert "http://localhost:4174" in settings.CORS_ORIGINS
    assert "http://127.0.0.1:4174" in settings.CORS_ORIGINS


@pytest.fixture()
def mock_redis():
    """Provide a fully-mocked Redis wrapper for auth tests."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture()
def mock_db_session():
    """Provide a fully-mocked async DB session."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute = AsyncMock(return_value=mock_result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def override_deps(mock_redis, mock_db_session):
    """Override FastAPI dependencies cleanly across all tests."""
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────
# /auth/request-otp
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_request_otp_success(mock_redis):
    """Returns 200, generates 6-digit OTP, stores in Redis with 300s TTL, and checks user existence."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/request-otp",
            json={"phone": "9876543210"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "OTP sent successfully"
    assert data["phone"] == "9876543210"
    assert data["expires_in_seconds"] == 300
    assert "is_new_user" in data
    assert len(data["dev_otp"]) == 6
    assert data["dev_otp"].isdigit()

    # Redis setex called with key, 300s, and 6-digit OTP
    mock_redis.setex.assert_called_once()
    key, ttl, otp = mock_redis.setex.call_args[0]
    assert key == "otp:9876543210"
    assert ttl == 300
    assert len(otp) == 6 and otp.isdigit()


@pytest.mark.asyncio
async def test_request_otp_reports_sms_delivery_failure(monkeypatch, mock_redis):
    provider = type("SMSProvider", (), {"send_otp": AsyncMock(return_value=False)})()
    monkeypatch.setattr(auth_endpoint, "get_sms_provider", lambda: provider)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/request-otp",
            json={"phone": "9876543210"},
        )

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Could not deliver OTP. Please try again later."
    mock_redis.delete.assert_any_call("otp:9876543210", "otp:attempts:9876543210")


@pytest.mark.asyncio
async def test_request_otp_rate_limiting(mock_redis):
    """Returns 429 when phone exceeds 3 requests within 10 minutes."""
    mock_redis.get = AsyncMock(return_value="3")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/request-otp",
            json={"phone": "9876543210"},
        )
    assert resp.status_code == 429
    assert "Too many OTP requests" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_request_otp_invalid_phone():
    """Returns 422 when phone is invalid."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/auth/request-otp", json={"phone": "123"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_request_otp_missing_phone():
    """Returns 422 when phone is absent."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/auth/request-otp", json={})
    assert resp.status_code == 422


# ─────────────────────────────────────────────────────────
# /auth/verify-otp
# ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_otp_expired_or_not_found(mock_redis):
    """Returns 400 when OTP is expired or not in Redis."""
    mock_redis.get = AsyncMock(return_value=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9876543210", "otp": "654321"}
        )
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_otp_wrong_code(mock_redis):
    """Returns 400 and increments attempts when OTP does not match."""
    # First call: attempts (None), Second call: stored OTP ("654321")
    mock_redis.get = AsyncMock(side_effect=[None, "654321"])
    mock_redis.incr = AsyncMock(return_value=1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9876543210", "otp": "111111"}
        )
    assert resp.status_code == 400
    assert "4 attempt(s) remaining" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_verify_otp_max_attempts_exceeded(mock_redis):
    """Returns 400 when max 5 verification attempts are exceeded."""
    mock_redis.get = AsyncMock(return_value="5")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9876543210", "otp": "123456"}
        )
    assert resp.status_code == 400
    assert "Maximum OTP verification attempts exceeded" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_verify_otp_new_user_requires_name(mock_redis, mock_db_session):
    """Returns 400 for new user when name is missing or invalid."""
    # attempts check returns None, stored OTP returns "123456"
    mock_redis.get = AsyncMock(side_effect=[None, "123456"])
    # mock_db_session returns None for user lookup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9876543210", "otp": "123456"}
        )
    assert resp.status_code == 400
    assert "Name is required for new users" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_verify_otp_success_new_user_creates_user_and_jwt_with_name(mock_redis, mock_db_session):
    """Successfully creates user with provided name and includes name in JWT payload."""
    mock_redis.get = AsyncMock(side_effect=[None, "123456"])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    async def fake_refresh(user):
        user.id = 42

    mock_db_session.refresh = AsyncMock(side_effect=fake_refresh)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9876543210", "otp": "123456", "name": "Ramesh Patil"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["name"] == "Ramesh Patil"
    assert data["user"]["id"] == 42

    # Verify JWT payload contains name
    decoded = decode_jwt_token(data["access_token"])
    assert decoded is not None
    assert decoded["name"] == "Ramesh Patil"
    assert decoded["user_id"] == 42


@pytest.mark.asyncio
async def test_verify_otp_provider_signup_creates_owner_profile(mock_redis, mock_db_session):
    mock_redis.get = AsyncMock(side_effect=[None, "123456"])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    async def assign_user_id():
        for call in mock_db_session.add.call_args_list:
            added = call.args[0]
            if isinstance(added, User):
                added.id = 42

    mock_db_session.flush = AsyncMock(side_effect=assign_user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9876543210", "otp": "123456", "name": "Machine Owner", "role": "provider"},
        )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "provider"
    provider = next(item for item in mock_db_session.add.call_args_list if isinstance(item.args[0], Provider)).args[0]
    assert provider.user_id == 42
    assert provider.org_type == "owner"
    assert provider.verified is False


@pytest.mark.asyncio
async def test_verify_otp_success_existing_user(mock_redis, mock_db_session):
    """Successfully authenticates existing user and returns existing name."""
    mock_redis.get = AsyncMock(side_effect=[None, "123456"])
    existing_user = User(
        name="Existing Farmer",
        phone="9876543210",
        role="farmer",
        language="en"
    )
    existing_user.id = 99
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db_session.execute.return_value = mock_result

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9876543210", "otp": "123456"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["name"] == "Existing Farmer"
    assert data["user"]["id"] == 99

    decoded = decode_jwt_token(data["access_token"])
    assert decoded["name"] == "Existing Farmer"


# ─────────────────────────────────────────────────────────
# Pydantic schema validation checks
# ─────────────────────────────────────────────────────────

def test_user_update_schema_validation():
    """UserUpdate validates name between 2 and 60 characters."""
    from pydantic import ValidationError
    from app.api.v1.endpoints.farmers import UserUpdate

    # Valid name
    u = UserUpdate(name="Ramesh Patil")
    assert u.name == "Ramesh Patil"

    # Too short (< 2)
    with pytest.raises(ValidationError):
        UserUpdate(name="R")

    # Too long (> 60)
    with pytest.raises(ValidationError):
        UserUpdate(name="A" * 61)

    # Missing name (required field)
    with pytest.raises(ValidationError):
        UserUpdate()
