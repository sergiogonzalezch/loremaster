"""Utilidades de autenticación con Clerk: caché JWKS y decodificación de tokens."""

import threading
import time
from typing import ClassVar

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings


class JWKSManager:
    """Gestiona la caché de claves JWKS de Clerk con TTL y thread-safety.

    Utiliza un :class:`httpx.Client` compartido para reutilizar conexiones
    y reduce la sobrecarga de crear un cliente nuevo en cada refresco.
    """

    _TTL: ClassVar[int] = 3600
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _cache: ClassVar[dict | None] = None
    _cache_time: ClassVar[float] = 0.0
    _client: ClassVar[httpx.Client] = httpx.Client(timeout=10.0)

    @classmethod
    def get_jwks(cls) -> dict:
        """Obtiene las claves públicas JWKS de Clerk con caché de 1 hora."""
        with cls._lock:
            if cls._cache is None or time.monotonic() - cls._cache_time > cls._TTL:
                try:
                    response = cls._client.get(settings.clerk_jwks_url)
                    response.raise_for_status()
                    cls._cache = response.json()
                    cls._cache_time = time.monotonic()
                except httpx.HTTPError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="No se pudo obtener las claves de Clerk",
                    ) from exc
            return cls._cache


def decode_clerk_token(token: str) -> dict:
    """Decodifica y valida un token JWT de Clerk."""
    clerk_issuer = settings.clerk_jwks_url.replace("/.well-known/jwks.json", "")
    try:
        return jwt.decode(
            token,
            JWKSManager.get_jwks(),
            algorithms=["RS256"],
            audience=settings.clerk_audience,
            issuer=clerk_issuer,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from exc
