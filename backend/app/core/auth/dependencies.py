"""Dependencias de autenticación para FastAPI.

Provee funciones de dependencia para proteger endpoints:
- get_current_user: Autenticación JWT local (cookie HttpOnly o Bearer token)
- get_admin_user: Autorización de administrador
"""

import hmac

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.auth import verify_token
from app.core.config import settings
from app.database import get_session
from app.models.db.user import User

_bearer = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None,
) -> str | None:
    """Extrae JWT desde header Authorization Bearer o cookie HttpOnly."""
    if bearer and bearer.scheme.lower() == "bearer":
        return bearer.credentials
    return request.cookies.get(settings.cookie_access_name)


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Obtiene el usuario autenticado desde cookie HttpOnly o Bearer token.

    Prioriza el header Authorization Bearer (para Swagger/herramientas), con
    fallback a la cookie HttpOnly. En todos los entornos el JWT es propio,
    firmado con SECRET_KEY.

    Args:
        request: Objeto Request para acceder a cookies y headers.
        session: Sesión de base de datos.
        bearer: Credenciales Bearer opcionales extraídas por FastAPI.

    Returns:
        Payload del JWT con sub (user_id), username, version, etc.

    Raises:
        HTTPException 401: Si no hay token, es inválido, el usuario fue eliminado
            o la versión del token no coincide (token revocado).

    """
    token = _extract_token(request, bearer)
    if not token:
        raise HTTPException(status_code=401, detail="No autorizado")

    payload = verify_token(token)

    user = session.get(User, payload["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="No autorizado")
    # Timing-safe comparison para token_version
    if not hmac.compare_digest(str(user.token_version), str(payload.get("version", 0))):
        raise HTTPException(status_code=401, detail="Sesión inválida")

    return payload


def get_current_user_optional(
    request: Request,
    session: Session = Depends(get_session),
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """Variante permisiva de get_current_user: retorna None si no hay sesión.

    Usada en endpoints que sirven contenido público pero ofrecen acceso
    extendido a usuarios autenticados (p.ej. /media para imágenes propias
    no compartidas).
    """
    try:
        return get_current_user(request, session, bearer)
    except HTTPException:
        return None


def get_admin_user(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Obtiene el usuario actual verificando que sea administrador.

    La autorización de admin se verifica desde la base de datos,
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
