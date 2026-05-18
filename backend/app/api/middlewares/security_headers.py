"""Middleware de headers de seguridad.

Añade headers de seguridad HTTP a todas las respuestas de la API.
Implementa protecciones contra XSS, clickjacking, MIME-sniffing y
ataques cross-window (Spectre).

Headers agregados:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restricciones ampliadas de permisos de navegador
    - Cache-Control: no-store (evita cacheo de respuestas autenticadas)
    - Cross-Origin-Opener-Policy: same-origin (protección Spectre)
    - Cross-Origin-Resource-Policy: same-origin
    - Strict-Transport-Security: HSTS (HTTPS directo o via X-Forwarded-Proto)
    - Content-Security-Policy: diferenciado por protocolo
"""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_PERMISSIONS_POLICY = (
    "geolocation=(), microphone=(), camera=(), "
    "payment=(), usb=(), display-capture=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade headers de seguridad a todas las respuestas HTTP.

    Referencias:
        - OWASP Secure Headers Project
        - Mozilla Web Security Guidelines
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = _PERMISSIONS_POLICY
        response.headers["Cache-Control"] = "no-store"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        # Media files must be embeddable cross-origin (images loaded by the frontend
        # on a different port). All other routes remain same-origin.
        if request.url.path.startswith("/media/"):
            response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        else:
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Detectar HTTPS tanto en conexión directa como detrás de proxy TLS
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        is_https = request.url.scheme == "https" or forwarded_proto == "https"

        if is_https:
            # preload solo cuando el dominio esté consolidado en HTTPS de forma permanente
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; "
                "img-src 'self' data: blob:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "object-src 'none';"
            )
        else:
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; "
                "img-src 'self' data: blob:; "
                "connect-src 'self' http://localhost:* ws://localhost:*; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "object-src 'none';"
            )
        response.headers["Content-Security-Policy"] = csp

        return response