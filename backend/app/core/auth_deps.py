from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.core.auth import verify_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="No autorizado")
    if settings.environment == "production":
        from app.api.routes.auth_clerk import decode_clerk_token
        return decode_clerk_token(credentials.credentials)
    return verify_token(credentials.credentials)
