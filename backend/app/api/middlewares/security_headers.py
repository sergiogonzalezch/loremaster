"""Middleware de headers de seguridad.

Añade headers de seguridad HTTP a todas las respuestas de la API.
Implementa protecciones contra XSS, clickjacking y MIME-sniffing (H-9).

Headers agregados:
    - X-Content-Type-Options: nosniff (evita MIME-sniffing)
    - X-Frame-Options: DENY (protección contra clickjacking)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restricciones de geolocalización, micrófono, cámara
    - Strict-Transport-Security: HSTS (solo en HTTPS)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade headers de seguridad a todas las respuestas HTTP.

    Referencias:
        - OWASP Secure Headers Project
        - Mozilla Web Security Guidelines
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Procesa la petición añadiendo headers de seguridad.

        Args:
            request: Petición HTTP entrante.
            call_next: Siguiente middleware/handler en la cadena.

        Returns:
            Response con headers de seguridad añadidos.
        """
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
