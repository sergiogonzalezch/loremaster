"""Endpoints de autenticación: login, registro y logout.

Implementa autenticación JWT con validación de credenciales,
registro de usuarios con validación de username, e invalidación
de tokens via token_version.
"""

import hmac
import re
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlmodel import Session

from app.core.auth import create_access_token, create_refresh_token, verify_refresh_token
from app.core.auth.csrf import generate_csrf_token
from app.core.auth.dependencies import get_current_user
from app.core.config import settings
from app.database import get_session
from app.models.db.user import User
from app.services.auth import authenticate_user, create_user, invalidate_session

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Payload para iniciar sesión con username/email y contraseña."""

    username_or_email: str
    password: str


class RegisterRequest(BaseModel):
    """Payload para registrar un nuevo usuario."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        r"""Valida que el username no contenga caracteres peligrosos."""
        if not re.match(r"^[A-Za-z0-9_-]{3,50}$", v):
            msg = "El nombre de usuario debe contener solo letras, números, guiones bajos y guiones"
            raise ValueError(
                msg,
            )
        return v


class AuthSuccessResponse(BaseModel):
    """Respuesta devuelta tras un login, registro o refresh exitoso."""

    message: str = "Autenticación exitosa"
    username: str
    access_token: str | None = None
    expires_at: datetime | None = None


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str | None = None) -> None:
    """Setea access token, CSRF y opcionalmente el refresh token."""
    csrf = generate_csrf_token()
    response.set_cookie(
        key=settings.cookie_access_name,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        key=settings.cookie_csrf_name,
        value=csrf,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        domain=settings.cookie_domain,
    )
    if refresh_token is not None:
        # path restringido al endpoint de refresh — el browser solo lo envía allí
        response.set_cookie(
            key=settings.cookie_refresh_name,
            value=refresh_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            path="/api/v1/auth/refresh",
            domain=settings.cookie_domain,
        )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.cookie_access_name, path="/", domain=settings.cookie_domain)
    response.delete_cookie(key=settings.cookie_csrf_name, path="/", domain=settings.cookie_domain)
    response.delete_cookie(key=settings.cookie_refresh_name, path="/api/v1/auth/refresh", domain=settings.cookie_domain)


@router.post("/login", response_model=AuthSuccessResponse)
def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
):
    """Autentica un usuario con username/email y contraseña."""
    user = authenticate_user(session, request.username_or_email, request.password)
    token_data = {"sub": user.id, "username": user.username, "version": user.token_version}
    access = create_access_token(data=token_data)
    refresh = create_refresh_token(data=token_data)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    _set_auth_cookies(response, access, refresh)
    result: dict = {"username": user.username, "expires_at": expires_at}
    if settings.environment == "local":
        result["access_token"] = access
    return result


@router.post("/register", response_model=AuthSuccessResponse)
def register(
    request: RegisterRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
):
    """Registra un nuevo usuario y setea cookies de autenticación."""
    user = create_user(session, request.username, request.email, request.password)
    token_data = {"sub": user.id, "username": user.username, "version": user.token_version}
    access = create_access_token(data=token_data)
    refresh = create_refresh_token(data=token_data)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    _set_auth_cookies(response, access, refresh)
    result: dict = {"username": user.username, "expires_at": expires_at}
    if settings.environment == "local":
        result["access_token"] = access
    return result


@router.post("/refresh", response_model=AuthSuccessResponse)
def refresh(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
):
    """Rota el access token usando el refresh token en cookie HttpOnly.

    Emite un nuevo access token + CSRF sin necesidad de credenciales.
    El refresh token permanece válido hasta su expiración (7 días) o hasta
    que el usuario haga logout (token_version incrementado).
    """
    refresh_tok = request.cookies.get(settings.cookie_refresh_name)
    if not refresh_tok:
        raise HTTPException(status_code=401, detail="No hay sesión activa")

    payload = verify_refresh_token(refresh_tok)

    user = session.get(User, payload["sub"])
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="No autorizado")

    if not hmac.compare_digest(str(user.token_version), str(payload.get("version", 0))):
        raise HTTPException(status_code=401, detail="Sesión inválida")

    token_data = {"sub": user.id, "username": user.username, "version": user.token_version}
    new_access = create_access_token(data=token_data)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    # Solo rota el access token y el CSRF; el refresh token sigue igual
    _set_auth_cookies(response, new_access)
    return {"username": user.username, "expires_at": expires_at}


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """Invalida la sesión del usuario y borra las cookies."""
    invalidate_session(session, current_user["sub"])
    _clear_auth_cookies(response)
