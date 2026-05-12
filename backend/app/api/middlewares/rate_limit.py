"""Middleware de rate limiting para la API.

Limita el número de requests por usuario en una ventana de tiempo.
Implementa protección contra brute force y DoS (P-2 / H-8).

El rate limiter opera en memoria (dict) con bloqueo por threading.Lock.
Para producción con múltiples workers, considerar Redis como backend.
"""

import base64
import json
import threading
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware simple de rate limiting por usuario.

    Limita requests por minuto por usuario identificado (JWT) o IP.
    Omite rate limiting en entornos de test y en endpoints de health.

    Attributes:
        requests_per_minute: Máximo de requests permitidos por ventana de 60s.
        requests: Dict que almacena timestamps de requests por user_id.
        lock: Lock de threading para acceso seguro al dict.
    """

    def __init__(self, app, requests_per_minute: int = 30):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: dict[str, list[float]] = {}
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: Callable):
        """Procesa la petición aplicando rate limiting.

        Solo aplica rate limiting a métodos que mutan estado
        (POST, PUT, PATCH, DELETE). Los GET y HEAD para carga de datos
        no se limitan para no afectar la experiencia del usuario.

        Args:
            request: Petición HTTP entrante.
            call_next: Siguiente middleware/handler en la cadena.

        Returns:
            Response del siguiente handler, o 429 si excede el límite.
        """
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        if settings.environment == "test":
            return await call_next(request)

        # Solo rate-limitar operaciones que mutan estado
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = request.cookies.get(settings.cookie_access_name)

        user_id = self._extract_user_from_token(token) if token else None
        if not user_id:
            user_id = request.client.host if request.client else "anonymous"

        if user_id and not self._check_rate_limit(user_id):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Demasiadas solicitudes. Intenta de nuevo en un minuto."
                },
            )

        return await call_next(request)

    def _extract_user_from_token(self, token: str) -> str | None:
        """Extrae el user_id (sub) del payload de un JWT.

        Args:
            token: Token JWT (formato header.payload.signature).

        Returns:
            user_id si se puede extraer, None en caso contrario.
        """
        try:
            parts = token.split(".")
            if len(parts) >= 2:
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
                return payload.get("sub")
        except (ValueError, KeyError, UnicodeDecodeError):
            return None
        return None

    def _check_rate_limit(self, user_id: str) -> bool:
        """Verifica si el usuario está dentro del límite de requests.

        Mantiene una ventana deslizante de 60 segundos.

        Args:
            user_id: Identificador del usuario (sub del JWT o IP).

        Returns:
            True si el request está permitido, False si excede el límite.
        """
        now = time.time()
        window_start = now - 60

        with self.lock:
            if user_id not in self.requests:
                self.requests[user_id] = []

            self.requests[user_id] = [
                t for t in self.requests[user_id] if t > window_start
            ]

            if len(self.requests[user_id]) >= self.requests_per_minute:
                return False

            self.requests[user_id].append(now)
            return True
