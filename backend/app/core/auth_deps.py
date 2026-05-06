from typing import Callable, Any
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.auth import verify_token as verify_local_token
from app.api.routes.auth_clerk import verify_clerk_token

security = HTTPBearer(auto_error=False)


def get_current_user_synced(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=401, detail="No autorizado")
    return verify_local_token(credentials)


def get_current_user_async(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=401, detail="No autorizado")
    import asyncio
    return asyncio.run(verify_clerk_token(credentials))


def get_current_user() -> Callable[..., Any]:
    if settings.environment == "production":
        return get_current_user_async
    return get_current_user_synced