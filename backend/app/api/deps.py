import redis.asyncio as aioredis
from typing import AsyncGenerator, Callable, List, Dict, Any, Optional, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_jwt_token
from app.models.user import User

security_bearer = HTTPBearer(auto_error=True)

import time

# In-memory Redis fallback cache for local dev / tests when Redis daemon is offline
# Stored as {key: (value, expire_at_timestamp)}
_in_memory_redis_store: Dict[str, Tuple[Any, Optional[float]]] = {}


class RedisWrapper:
    """Wrapper that attempts real Redis commands, falling back to in-memory store if Redis is offline."""
    def __init__(self, real_redis=None):
        self.real_redis = real_redis

    async def get(self, key: str) -> Optional[str]:
        if self.real_redis:
            try:
                val = await self.real_redis.get(key)
                if val:
                    return val.decode("utf-8") if isinstance(val, bytes) else str(val)
            except Exception:
                pass
        entry = _in_memory_redis_store.get(key)
        if entry is None:
            return None
        val, exp = entry
        if exp is not None and time.time() > exp:
            _in_memory_redis_store.pop(key, None)
            return None
        return str(val)

    async def setex(self, key: str, time_sec: int, value: str):
        if self.real_redis:
            try:
                await self.real_redis.setex(key, time_sec, value)
                return
            except Exception:
                pass
        _in_memory_redis_store[key] = (str(value), time.time() + time_sec)

    async def incr(self, key: str) -> int:
        if self.real_redis:
            try:
                return await self.real_redis.incr(key)
            except Exception:
                pass
        current_str = await self.get(key)
        current = int(current_str) + 1 if current_str else 1
        existing_exp = _in_memory_redis_store.get(key, (None, None))[1]
        _in_memory_redis_store[key] = (str(current), existing_exp)
        return current

    async def expire(self, key: str, time_sec: int):
        if self.real_redis:
            try:
                await self.real_redis.expire(key, time_sec)
                return
            except Exception:
                pass
        if key in _in_memory_redis_store:
            val = _in_memory_redis_store[key][0]
            _in_memory_redis_store[key] = (val, time.time() + time_sec)

    async def delete(self, *keys: str) -> int:
        if self.real_redis:
            try:
                return await self.real_redis.delete(*keys)
            except Exception:
                pass
        count = 0
        for k in keys:
            if k in _in_memory_redis_store:
                _in_memory_redis_store.pop(k, None)
                count += 1
        return count


async def get_redis() -> AsyncGenerator[RedisWrapper, None]:
    real_redis = None
    try:
        real_redis = aioredis.from_url(settings.REDIS_URL, socket_timeout=1.5)
        await real_redis.ping()
    except Exception:
        real_redis = None

    wrapper = RedisWrapper(real_redis)
    try:
        yield wrapper
    finally:
        if real_redis:
            await real_redis.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_jwt_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    stmt = select(User).where(User.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


def require_role(*allowed_roles: str) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation restricted to roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker
