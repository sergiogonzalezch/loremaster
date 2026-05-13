"""Endpoints de autenticación: login, registro y logout.

Implementa autenticación JWT con validación de credenciales,
registro de usuarios con validación de username, e invalidación
de tokens via token_version.
"""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlmodel import Session

from app.core.auth import create_access_token
from app.core.auth.csrf import generate_csrf_token
from app.core.auth.dependencies import get_current_user
from app.core.config import settings
from app.database import get_session
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
    """Respuesta devuelta tras un login o registro exitoso."""

    message: str = "Autenticación exitosa"
    username: str


def _set_auth_cookies(response: Response, token: str) -> None:
    csrf = generate_csrf_token()
    response.set_cookie(
        key=settings.cookie_access_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=settings.cookie_path,
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        key=settings.cookie_csrf_name,
        value=csrf,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=settings.cookie_path,
        domain=settings.cookie_domain,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.cookie_access_name,
        path=settings.cookie_path,
        domain=settings.cookie_domain,
    )
    response.delete_cookie(
        key=settings.cookie_csrf_name,
        path=settings.cookie_path,
        domain=settings.cookie_domain,
    )


@router.post("/login", response_model=AuthSuccessResponse)
def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
):
    """Autentica un usuario con username/email y contraseña."""
    user = authenticate_user(session, request.username_or_email, request.password)
    token = create_access_token(
        data={"sub": user.id, "username": user.username, "version": user.token_version},
    )
    _set_auth_cookies(response, token)
    return {"username": user.username}


@router.post("/register", response_model=AuthSuccessResponse)
def register(
    request: RegisterRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
):
    """Registra un nuevo usuario y setea cookies de autenticación."""
    user = create_user(session, request.username, request.email, request.password)
    token = create_access_token(
        data={"sub": user.id, "username": user.username, "version": user.token_version},
    )
    _set_auth_cookies(response, token)
    return {"username": user.username}


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    current_user: Annotated[dict, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    """Invalida la sesión del usuario y borra las cookies."""
    invalidate_session(session, current_user["sub"])
    _clear_auth_cookies(response)
