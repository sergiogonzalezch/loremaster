"""Rutas de autenticación mediante Clerk."""

import threading
import time
from typing import ClassVar

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session

from app.core.config import settings
from app.database import get_session
from app.models.db.user import User

router = APIRouter(prefix="/auth/clerk", tags=["auth"])
security = HTTPBearer(auto_error=False)


class JWKSManager:
    """Gestiona la caché de claves JWKS de Clerk con TTL y thread-safety.

    Utiliza un :class:`httpx.Client` compartido para reutilizar conexiones
    y reduce la sobrecarga de crear un cliente nuevo en cada refresco.
    """

    _TTL: ClassVar[int] = 3600  # 1 hora; Clerk rota claves ocasionalmente
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _cache: ClassVar[dict | None] = None
    _cache_time: ClassVar[float] = 0.0
    _client: ClassVar[httpx.Client] = httpx.Client(timeout=10.0)

    @classmethod
    def get_jwks(cls) -> dict:
        """Obtiene las claves públicas JWKS de Clerk con caché de 1 hora.

        Returns:
            Diccionario con las claves JWKS.

        Raises:
            HTTPException(503): Si no se puede conectar con Clerk.

        """
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


def get_jwks() -> dict:
    """Obtiene las claves públicas JWKS de Clerk con caché de 1 hora.

    Returns:
        Diccionario con las claves JWKS.

    Raises:
        HTTPException(503): Si no se puede conectar con Clerk.

    """
    return JWKSManager.get_jwks()


def decode_clerk_token(token: str) -> dict:
    """Decodifica y valida un token JWT de Clerk.

    Args:
        token: Token JWT de Clerk.

    Returns:
        Payload decodificado del token.

    Raises:
        HTTPException(401): Si el token es inválido o ha expirado.

    """
    clerk_issuer = settings.clerk_jwks_url.replace("/.well-known/jwks.json", "")
    try:
        return jwt.decode(
            token,
            get_jwks(),
            algorithms=["RS256"],
            audience=settings.clerk_audience,
            issuer=clerk_issuer,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido",
        ) from exc


@router.get("/verify")
def verify(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
):
    """Verifica la validez de un token Bearer de Clerk.

    Valida que el usuario exista en la BD y no esté eliminado (M-5).

    Returns:
        Diccionario con valid=True y el user_id del token.

    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado",
        )
    payload = decode_clerk_token(credentials.credentials)
    user_id = payload.get("sub")
    user = session.get(User, user_id)
    if not user or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado",
        )
    return {"valid": True, "user_id": user_id}
