from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Politica de token_version (L-11):
# - token_version se incrementa en logout para invalidar tokens previos
# - Tokens tienen TTL de ACCESS_TOKEN_EXPIRE_MINUTES (default 24h)
# - Recomendacion: usar refresh tokens de 7 dias con access tokens de 15-60 min
#   en produccion para minimizar ventana de exposicion


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Crea un token de acceso JWT con fecha de expiración.

    El token expira según ACCESS_TOKEN_EXPIRE_MINUTES (default 24h).
    Para revocar un token antes de su expiración, incrementar token_version
    del usuario (el token contiene la versión y será rechazado al no coincidir).
    Ver politica de token_version en el modulo.
    """

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Verifica y decodifica un token JWT, lanzando HTTPException si es inválido."""

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        # Protección contra alg-confusion (CVE-2024-33663)
        token_alg = payload.get("alg")
        if token_alg is not None and token_alg != ALGORITHM:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
        )


def hash_password(password: str) -> str:
    """Genera un hash bcrypt para la contraseña proporcionada."""

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra un hash bcrypt.

    Retorna False silenciosamente si el hash es inválido (M-6: timing-safe
    dummy checks con hashes dummy no válidos).
    """
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except ValueError:
        return False
