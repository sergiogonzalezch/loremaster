"""Utilidades de autenticación JWT y hashing de contraseñas."""

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Hash dummy válido (60 chars) generado una vez al arrancar para la protección
# de timing en authenticate_user cuando el usuario no existe.
# bcrypt.checkpw lanza ValueError para hashes <60 chars, dejando el timing en 0ms.
DUMMY_HASH: str = bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt()).decode()

# Politica de token_version:
# - token_version se incrementa en logout para invalidar tokens previos
# - Tokens tienen TTL de ACCESS_TOKEN_EXPIRE_MINUTES (default 60min)
# - Recomendacion: usar refresh tokens de 7 dias con access tokens de 15-60 min
#   en produccion para minimizar ventana de exposicion


def create_refresh_token(data: dict) -> str:
    """Crea un refresh token JWT de larga duración (7 días por defecto).

    El claim ``type=refresh`` evita que se use como access token.
    Se invalida incrementando token_version en logout.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_refresh_token(token: str) -> dict:
    """Verifica un refresh token. Lanza HTTPException 401 si es inválido o no es de tipo refresh."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None or payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from e
    return payload


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Crea un token de acceso JWT con fecha de expiración.

    El token expira según ACCESS_TOKEN_EXPIRE_MINUTES (default 60min).
    Para revocar un token antes de su expiración, incrementar token_version
    del usuario (el token contiene la versión y será rechazado al no coincidir).
    Ver politica de token_version en el modulo.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Verifica y decodifica un token JWT, lanzando HTTPException si es inválido."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )
        # Protección contra alg-confusion (CVE-2024-33663)
        token_alg = payload.get("alg")
        if token_alg is not None and token_alg != ALGORITHM:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from e
    else:
        return payload


def hash_password(password: str) -> str:
    """Genera un hash bcrypt para la contraseña proporcionada."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra un hash bcrypt."""
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except ValueError:
        return False
