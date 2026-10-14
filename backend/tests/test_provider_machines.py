from datetime import date
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile

from app.api.v1.endpoints.provider_machines import MachineUpdatePayload, update_machine
from app.api.v1.endpoints.uploads import upload_machine_photos
from app.models.machine import Machine
from app.models.user import Provider, User


def _result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _user(user_id=1):
    return User(id=user_id, name="Provider", phone=f"98765432{user_id:02d}", role="provider")


@pytest.mark.asyncio
async def test_provider_cannot_update_another_providers_machine():
    current_user = _user(1)
    provider = Provider(user_id=current_user.id, org_type="owner", verified=False)
    machine = Machine(
        id=9,
        provider_id=2,
        machine_type_id=1,
        location="POINT(73.8 18.5)",
        rate_per_acre=100,
        available_from=date.today(),
        available_to=date.today(),
    )
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_result(provider), _result(machine)])

    with pytest.raises(HTTPException) as error:
        await update_machine(
            9,
            MachineUpdatePayload(rate_per_acre=200),
            current_user=current_user,
            db=db,
        )

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_machine_photo_upload_rejects_pdf():
    current_user = _user()
    machine = Machine(id=9, provider_id=current_user.id)
    db = AsyncMock()
    db.execute.return_value = _result(machine)
    upload = UploadFile(
        file=BytesIO(b"%PDF-1.7"),
        filename="manual.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )

    with pytest.raises(HTTPException) as error:
        await upload_machine_photos(9, [upload], current_user, db)

    assert error.value.status_code == 415
    assert "Only JPEG and PNG" in error.value.detail


@pytest.mark.asyncio
async def test_machine_photo_upload_rejects_files_over_five_megabytes():
    current_user = _user()
    machine = Machine(id=9, provider_id=current_user.id)
    db = AsyncMock()
    db.execute.return_value = _result(machine)
    upload = UploadFile(
        file=BytesIO(b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024)),
        filename="large.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )

    with pytest.raises(HTTPException) as error:
        await upload_machine_photos(9, [upload], current_user, db)

    assert error.value.status_code == 413
    assert "5 MB" in error.value.detail