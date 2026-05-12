"""Dependencias de autenticación para FastAPI.

Provee funciones de dependencia para proteger endpoints:
- get_current_user: Autenticación JWT (local) o Clerk (producción)
- get_admin_user: Autorización de administrador
"""

import hmac

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session

from app.core.auth import verify_token
from app.core.config import settings
from app.database import get_session
from app.models.db.user import User


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """Obtiene el usuario autenticado desde la cookie HttpOnly.

    Lee el JWT de la cookie 'access_token' en lugar del header Authorization.
    Valida firma, existencia de usuario, soft-delete y token_version.

    En producción (environment="production"), delega la verificación
    a Clerk (C-1) pero sigue leyendo de la cookie local.

    Args:
        request: Objeto Request para acceder a cookies.
        session: Sesión de base de datos.

    Returns:
        Payload del JWT con sub (user_id), username, version, etc.

    Raises:
        HTTPException 401: Si no hay cookie, es inválido, el usuario fue eliminado
            o la versión del token no coincide (token revocado).

    """
    token = request.cookies.get(settings.cookie_access_name)
    if not token:
        raise HTTPException(status_code=401, detail="No autorizado")

    if settings.environment == "production":
        # Lazy import: Clerk no es requerido en entornos locales (C-1).
        from app.api.routes.auth.auth_clerk import decode_clerk_token  # noqa: PLC0415

        payload = decode_clerk_token(token)
        user = session.get(User, payload.get("sub"))
        if not user or user.is_deleted:
            raise HTTPException(status_code=401, detail="No autorizado")
        # Verificar token_version si existe en el token de Clerk (custom claim)
        if "version" in payload and not hmac.compare_digest(
            str(user.token_version), str(payload.get("version", 0))
        ):
            raise HTTPException(status_code=401, detail="Sesión inválida")
        return payload

    payload = verify_token(token)

    user = session.get(User, payload["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="No autorizado")
    # Timing-safe comparison para token_version (L-7)
    if not hmac.compare_digest(str(user.token_version), str(payload.get("version", 0))):
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
