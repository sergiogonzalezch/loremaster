"""Generación y validación de tokens CSRF.

Implementa la defensa Double Submit Cookie contra CSRF (H-14, M-17).
El backend genera un token aleatorio que se envía como cookie legible por JS
y el frontend lo devuelve en el header X-CSRF-Token en cada mutación.
"""

import secrets

from fastapi import Request, HTTPException

from app.core.config import settings


def generate_csrf_token() -> str:
    """Genera un token CSRF criptográficamente seguro."""
    return secrets.token_urlsafe(32)


def validate_csrf(request: Request) -> None:
    """Valida que el header X-CSRF-Token coincida con la cookie csrf_token.

    Raises:
        HTTPException 403: Si falta el token o no coincide.
    """
    cookie_token = request.cookies.get(settings.cookie_csrf_name)
    header_token = request.headers.get("x-csrf-token")

    if not cookie_token or not header_token:
        raise HTTPException(status_code=403, detail="CSRF token faltante")

    if not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF token inválido")
