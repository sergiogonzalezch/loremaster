"""Rutas de autenticación mediante Clerk."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.api.routes.auth.auth import AuthSuccessResponse, _set_auth_cookies
from app.core.auth import create_access_token, create_refresh_token
from app.core.auth.clerk import decode_clerk_token
from app.core.config import settings
from app.database import get_session
from app.models.db.user import User
from app.services.auth import get_or_create_clerk_user

router = APIRouter(prefix="/auth/clerk", tags=["auth"])
security = HTTPBearer(auto_error=False)


@router.post("/sync")
def sync_clerk_user(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> AuthSuccessResponse:
    """Intercambia un Clerk JWT por una sesión local (cookies HttpOnly).

    El frontend envía el Clerk JWT una sola vez en el header Authorization.
    El backend valida el token RS256, crea o encuentra el User en la BD local,
    emite un JWT propio y setea las cookies de sesión. Requests posteriores
    usan las cookies sin necesidad de reenviar el Clerk JWT.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")

    clerk_token = auth_header.split(" ", 1)[1]
    payload = decode_clerk_token(clerk_token)

    user = get_or_create_clerk_user(session, payload)
    token_data = {"sub": user.id, "username": user.username, "version": user.token_version}
    access = create_access_token(data=token_data)
    refresh = create_refresh_token(data=token_data)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    _set_auth_cookies(response, access, refresh)
    return AuthSuccessResponse(username=user.username, expires_at=expires_at)


@router.get("/verify")
def verify(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[Session, Depends(get_session)],
):
    """Verifica la validez de un token Bearer de Clerk.

    Valida que el usuario exista en la BD y no esté eliminado.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
        )
    payload = decode_clerk_token(credentials.credentials)
    user_id = payload.get("sub")
    user = session.get(User, user_id)
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    return {"valid": True, "user_id": user_id}
