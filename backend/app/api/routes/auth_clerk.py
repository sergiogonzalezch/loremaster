from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from functools import lru_cache

from app.core.config import settings

router = APIRouter(prefix="/auth/clerk", tags=["auth"])
security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_cached_jwks() -> dict:
    try:
        response = httpx.get(settings.clerk_jwks_url, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo obtener las claves de Clerk"
        )


async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="No autorizado")

    token = credentials.credentials
    jwks = get_cached_jwks()

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.clerk_audience,
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.get("/verify")
def verify(clerk_payload: dict = Depends(verify_clerk_token)):
    return {"valid": True, "user_id": clerk_payload.get("sub")}