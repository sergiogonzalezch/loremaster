from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from app.core.config import settings
from app.core.auth import verify_token
from app.database import get_session
from app.models.db.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> dict:
    """Obtiene el usuario autenticado desde el token JWT.

    Lanza HTTPException 401 si no hay token, es inválido, el usuario fue eliminado
    o la versión del token no coincide con la del usuario.
    En producción, delega la verificación en Clerk.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="No autorizado")
    if settings.environment == "production":
        from app.api.routes.auth.auth_clerk import decode_clerk_token

        return decode_clerk_token(credentials.credentials)

    payload = verify_token(credentials.credentials)

    user = session.get(User, payload["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="No autorizado")
    if user.token_version != payload.get("version", 0):
        raise HTTPException(status_code=401, detail="Sesión inválida")

    return payload


def get_admin_user(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Obtiene el usuario actual verificando que sea administrador.

    Lanza HTTPException 403 si el usuario no es administrador.
    """
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted or not user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return current_user
