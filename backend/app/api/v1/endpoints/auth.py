import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_jwt_token
from app.api.deps import get_redis, RedisWrapper
from app.models.user import User
from app.services.sms import get_sms_provider

router = APIRouter()


class RequestOTPInput(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")


class VerifyOTPInput(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    otp: str = Field(..., min_length=6, max_length=6)
    name: Optional[str] = Field(None, min_length=2, max_length=60)


class RefreshTokenInput(BaseModel):
    refresh_token: str


@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(
    payload: RequestOTPInput,
    db: AsyncSession = Depends(get_db),
    redis: RedisWrapper = Depends(get_redis)
):
    phone = payload.phone.strip()
    rate_limit_key = f"ratelimit:otp:{phone}"
    otp_key = f"otp:{phone}"
    attempts_key = f"otp:attempts:{phone}"

    # Check Rate Limit (max 3 requests per 10 minutes)
    current_count_str = await redis.get(rate_limit_key)
    current_count = int(current_count_str) if current_count_str else 0

    if current_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests for this phone number. Please try again after 10 minutes."
        )

    # Generate 6-digit cryptographically secure random OTP
    otp = str(secrets.randbelow(900000) + 100000)

    # Store in Redis with 5-minute TTL (300 seconds)
    await redis.setex(otp_key, 300, otp)

    # Reset failed attempts counter
    await redis.delete(attempts_key)

    # Increment rate limit counter (600 seconds TTL = 10 minutes)
    new_count = await redis.incr(rate_limit_key)
    if new_count == 1:
        await redis.expire(rate_limit_key, 600)

    # Send OTP via SMS Provider adapter
    sms_provider = get_sms_provider()
    await sms_provider.send_otp(phone, otp)

    # Check if user already exists
    stmt = select(User).where(User.phone == phone)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    is_new_user = existing_user is None

    response_data = {
        "message": "OTP sent successfully",
        "phone": phone,
        "expires_in_seconds": 300,
        "is_new_user": is_new_user
    }

    # For local testing/dev, provide dev_otp in non-production environments
    if settings.APP_ENV != "production":
        response_data["dev_otp"] = otp

    return response_data


@router.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(
    payload: VerifyOTPInput,
    db: AsyncSession = Depends(get_db),
    redis: RedisWrapper = Depends(get_redis)
):
    phone = payload.phone.strip()
    otp = payload.otp.strip()
    otp_key = f"otp:{phone}"
    attempts_key = f"otp:attempts:{phone}"

    # Check attempts rate limit (max 5 attempts)
    attempts_str = await redis.get(attempts_key)
    attempts = int(attempts_str) if attempts_str else 0

    if attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum OTP verification attempts exceeded. Please request a new OTP."
        )

    stored_otp = await redis.get(otp_key)

    if not stored_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired or was not requested. Please request a new OTP."
        )

    if otp != stored_otp:
        new_attempts = await redis.incr(attempts_key)
        if new_attempts == 1:
            await redis.expire(attempts_key, 300)
        remaining = max(0, 5 - new_attempts)
        if remaining == 0:
            await redis.delete(otp_key)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP. Maximum attempts reached. Please request a new OTP."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempt(s) remaining."
        )

    # Clean up OTP keys on success
    await redis.delete(otp_key, attempts_key)

    # Query or Create User
    stmt = select(User).where(User.phone == phone)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        clean_name = (payload.name or "").strip()
        if not clean_name or len(clean_name) < 2 or len(clean_name) > 60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name is required for new users and must be between 2 and 60 characters."
            )
        user = User(
            name=clean_name,
            phone=phone,
            role="farmer",
            language="en"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if payload.name:
            clean_name = payload.name.strip()
            if len(clean_name) < 2 or len(clean_name) > 60:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Name must be between 2 and 60 characters."
                )
            user.name = clean_name
            await db.commit()
            await db.refresh(user)

    access_token = create_access_token(user_id=user.id, role=user.role, name=user.name)
    refresh_token = create_refresh_token(user_id=user.id, role=user.role, name=user.name)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "role": user.role,
            "language": user.language
        }
    }


@router.post("/refresh-token", status_code=status.HTTP_200_OK)
async def refresh_token_endpoint(
    payload: RefreshTokenInput,
    db: AsyncSession = Depends(get_db)
):
    decoded = decode_jwt_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    user_id = decoded.get("user_id")
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with token not found"
        )

    new_access_token = create_access_token(user_id=user.id, role=user.role, name=user.name)
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }
