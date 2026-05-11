"""Dependencias de autenticación para FastAPI.

Provee funciones de dependencia para proteger endpoints:
- get_current_user: Autenticación JWT (local) o Clerk (producción)
- get_admin_user: Autorización de administrador
"""

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

    En entornos locales, verifica el token JWT firmado con SECRET_KEY,
    valida que el usuario exista y no esté eliminado, y comprueba
    la versión del token (token_version) para invalidación.

    En producción (environment="production"), delega la verificación
    a Clerk (C-1).

    Args:
        credentials: Credenciales del header Authorization: Bearer.
        session: Sesión de base de datos.

    Returns:
        Payload del JWT con sub (user_id), username, version, etc.

    Raises:
        HTTPException 401: Si no hay token, es inválido, el usuario fue eliminado
            o la versión del token no coincide (token revocado).
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

    Implementa H-1: la autorización de admin se verifica desde la base de datos,
    no desde el JWT (is_admin fue eliminado del token por seguridad).

    Args:
        current_user: Usuario autenticado (de get_current_user).
        session: Sesión de base de datos.

    Returns:
        Payload del usuario autenticado.

    Raises:
        HTTPException 403: Si el usuario no es administrador o está eliminado.
    """
    user = session.get(User, current_user["sub"])
    if not user or user.is_deleted or not user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return current_user
