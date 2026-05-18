"""Middleware de rate limiting para la API.

Limita el número de requests por usuario en una ventana deslizante de 60s.
Usa Redis (sorted sets) como backend para garantizar aislamiento entre workers.
Aplica límites diferenciados según el tipo de endpoint (base, LLM, imagen).

El user_id se extrae verificando la firma del JWT (jose). Si el token es
inválido o no existe, se usa la IP del cliente como fallback.

Si Redis no está disponible, la petición se deja pasar (fail-open)
para evitar bloquear la aplicación por una caída de caché.
"""

import time
from collections.abc import Callable

import redis.asyncio as aioredis
from jose import JWTError
from jose import jwt as jose_jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import settings

_LLM_PATH_SUFFIXES = ("/query", "/image-generation/build-prompt")
_IMAGE_PATH_SUFFIXES = ("/image-generation/generate",)

_EXEMPT_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting por usuario con backend Redis.

    Attributes:
        requests_per_minute: Límite base de requests por ventana de 60s.
        redis: Cliente Redis async compartido por todos los workers.

    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 30) -> None:  # noqa: D107
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.redis: aioredis.Redis = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:  # noqa: D102
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        if not settings.rate_limit_enabled or settings.environment == "test":
            return await call_next(request)

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        token = self._extract_token(request)
        user_id = self._extract_user_from_token(token) if token else None
        if not user_id:
            user_id = request.client.host if request.client else "anonymous"

        limit = self._get_limit_for_path(request.url.path)
        if not await self._check_rate_limit(user_id, limit):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Demasiadas solicitudes. Intenta de nuevo en un minuto.",
                },
            )

        return await call_next(request)

    def _extract_token(self, request: Request) -> str | None:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        return request.cookies.get(settings.cookie_access_name)

    def _extract_user_from_token(self, token: str) -> str | None:
        try:
            payload = jose_jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            return payload.get("sub")
        except (JWTError, Exception):  # noqa: BLE001
            return None

    def _get_limit_for_path(self, path: str) -> int:
        if any(path.endswith(s) for s in _LLM_PATH_SUFFIXES):
            return settings.rate_limit_llm_per_minute
        if any(path.endswith(s) for s in _IMAGE_PATH_SUFFIXES):
            return settings.rate_limit_image_per_minute
        return self.requests_per_minute

    async def _check_rate_limit(self, user_id: str, limit: int) -> bool:
        now = time.time()
        window_start = now - 60
        key = f"rl:{user_id}"
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, 61)
                results = await pipe.execute()
            count: int = results[2]
            return count <= limit
        except Exception:  # noqa: BLE001
            return True  # Redis unavailable — fail-open to avoid blocking the app
