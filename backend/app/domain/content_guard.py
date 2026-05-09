"""Guardia de contenido: validación de entrada de usuarios, documentos y salida del LLM.

Aplica patrones de expresiones regulares para detectar contenido no permitido
antes de procesarlo o tras generarlo.
"""

import re
import unicodedata

from app.core.exceptions import ContentNotAllowedError, GeneratedContentBlockedError

# Patrones aplicados a entrada de usuarios y documentos: bloquean cualquier mención de acciones dañinas.
_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(porn|porno|xxx|explicit\s+sexual|sexo\s+expl[íi]cito)\b", re.I),
    re.compile(r"\b(hate\s+speech|supremac(?:y|ista)|genocid(?:e|io)|slur)\b", re.I),
    re.compile(
        r"\b(make|build|fabricar|crear)\s+((a|an|un|una)\s+)?(bomb|bomba|weapon|arma)\b",
        re.I,
    ),
    re.compile(
        r"\b(synthesize|sintetizar|s[íi]ntesis|fabricar|cocinar)\s+(drugs?|drogas?|meth)\b",
        re.I,
    ),
    re.compile(
        r"\b(acoso|harass(?:ment)?|denigrate|denigrar|humill(?:ar|ation))\b",
        re.I,
    ),
)
"""Patrones para bloquear contenido en entrada de usuarios y documentos."""

# Patrones aplicados a salida del LLM: arma/bomba requieren enmarcado explícito instructivo
# para evitar falsos positivos cuando contenido narrativo de fantasía menciona armas en contexto.
_OUTPUT_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(porn|porno|xxx|explicit\s+sexual|sexo\s+expl[íi]cito)\b", re.I),
    re.compile(r"\b(hate\s+speech|supremac(?:y|ista)|genocid(?:e|io)|slur)\b", re.I),
    re.compile(
        r"\b(c[oó]mo|instrucciones?)\s+(para\s+)?(make|build|fabricar|crear)\s+((a|an|un|una)\s+)?(bomb|bomba|weapon|arma)\b",
        re.I,
    ),
    re.compile(
        r"\b(synthesize|sintetizar|s[íi]ntesis|fabricar|cocinar)\s+(drugs?|drogas?|meth)\b",
        re.I,
    ),
    re.compile(
        r"\b(acoso|harass(?:ment)?|denigrate|denigrar|humill(?:ar|ation))\b",
        re.I,
    ),
)
"""Patrones para bloquear contenido en salida generada por el LLM."""


def _normalize(text: str) -> str:
    """Normaliza texto para comparación insensible a acentos.

    NFKD descompone ligaduras/caracteres de ancho completo; eliminar Mn quita diacríticos
    combinados de modo que é→e, ó→o, etc., habilitando coincidencia insensible a acentos.
    """
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()


def _check_text(
    text: str, error: Exception, patterns: tuple[re.Pattern[str], ...]
) -> None:
    """Verifica texto contra patrones bloqueados y lanza la excepción dada si coincide."""
    normalized = _normalize(text)
    for pattern in patterns:
        if pattern.search(normalized):
            raise error


def check_user_input(text: str) -> None:
    """Verifica que el texto de entrada del usuario no contenga contenido bloqueado.

    Lanza ContentNotAllowedError si se detecta contenido no permitido.
    """
    _check_text(
        text, ContentNotAllowedError("Contenido no permitido.", text), _BLOCKED_PATTERNS
    )


def check_document_content(text: str) -> None:
    """Verifica que el texto extraído de un documento no contenga contenido bloqueado.

    Lanza ContentNotAllowedError si se detecta contenido no permitido.
    """
    _check_text(
        text,
        ContentNotAllowedError("El documento contiene contenido no permitido.", text),
        _BLOCKED_PATTERNS,
    )


def check_generated_output(text: str) -> None:
    """Verifica que la salida generada por el LLM no contenga contenido bloqueado.

    Lanza GeneratedContentBlockedError si se detecta contenido no permitido.
    """
    _check_text(text, GeneratedContentBlockedError(text), _OUTPUT_BLOCKED_PATTERNS)
