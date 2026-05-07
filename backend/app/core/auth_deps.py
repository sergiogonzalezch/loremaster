from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.config import settings
from app.core.auth import verify_token
from app.database import get_session
from app.models.users import User

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


def get_admin_user(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted or not user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return current_user
