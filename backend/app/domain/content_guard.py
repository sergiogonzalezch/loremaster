"""Guardia de contenido: validación de entrada de usuarios, documentos y salida del LLM.

Aplica patrones de expresiones regulares para detectar contenido no permitido
antes de procesarlo o tras generarlo.

LIMITACIONES CONOCIDAS (M-1):
- Este modulo es una primera linea de defensa, no una barrera exhaustiva.
- No detecta: jailbreaks estructurales, leetspeak (e.g. "b0mb"), base64, ROT13,
  inyeccion de prompts via delimitadores, o tecnicas de evasion avanzadas.
- Requiere complemento con: validacion de esquemas de salida, rate limiting,
  monitoreo de comportamiento anomalo, y revision humana para casos criticos.

MITIGACION ReDoS (M-2):
- Se aplica limite de longitud (100KB) antes de normalizar con NFKD.
- Texto que exceda el limite se trunca para evitar bloqueo del worker.
"""

import logging
import re
import unicodedata

from app.core.exceptions import ContentNotAllowedError, GeneratedContentBlockedError

logger = logging.getLogger(__name__)

# Sustituciones leetspeak comunes para evasión de filtros (M-1)
# 0→o, 1→i, 3→e, 4→a, 5→s, 6→g, @→a, $→s
_LEET_TABLE = str.maketrans("013456@$", "oieasgas")

# Limite de longitud para prevenir ReDoS/CPU-DoS (M-2)
_MAX_TEXT_LENGTH = 100_000  # 100 KB

# Patrones aplicados a entrada de usuarios y documentos: bloquean cualquier mención de acciones dañinas.
_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(porn|porno|xxx|explicit\s+sexual|sexo\s+expl[íi]cito)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(hate\s+speech|supremac(?:y|ista)|genocid(?:e|io)|slur)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(make|build|fabricar|crear)\s+((a|an|un|una)\s+)?(bomb|bomba|weapon|arma)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(synthesize|sintetizar|s[íi]ntesis|fabricar|cocinar)\s+(drugs?|drogas?|meth)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(acoso|harass(?:ment)?|denigrate|denigrar|humill(?:ar|ation))\b",
        re.IGNORECASE,
    ),
)
"""Patrones para bloquear contenido en entrada de usuarios y documentos."""

# Patrones aplicados a salida del LLM: arma/bomba requieren enmarcado explícito instructivo
# para evitar falsos positivos cuando contenido narrativo de fantasía menciona armas en contexto.
_OUTPUT_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(porn|porno|xxx|explicit\s+sexual|sexo\s+expl[íi]cito)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(hate\s+speech|supremac(?:y|ista)|genocid(?:e|io)|slur)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(c[oó]mo|instrucciones?)\s+(para\s+)?(make|build|fabricar|crear)\s+((a|an|un|una)\s+)?(bomb|bomba|weapon|arma)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(synthesize|sintetizar|s[íi]ntesis|fabricar|cocinar)\s+(drugs?|drogas?|meth)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(acoso|harass(?:ment)?|denigrate|denigrar|humill(?:ar|ation))\b",
        re.IGNORECASE,
    ),
)
"""Patrones para bloquear contenido en salida generada por el LLM."""


def _normalize(text: str) -> str:
    """Normaliza texto para comparación robusta contra evasiones comunes (M-1, M-2).

    Pasos:
    1. Trunca a _MAX_TEXT_LENGTH para prevenir ReDoS (M-2).
    2. NFKD + elimina diacríticos: é→e, ó→o, caracteres de ancho completo.
    3. Lowercase.
    4. Sustituye leetspeak (_LEET_TABLE): 0→o, 1→i, 3→e, @→a, $→s, etc.
    5. Colapsa chars repetidos (bbooommmb→bomb) para evadir filtros por repetición.
    """
    if len(text) > _MAX_TEXT_LENGTH:
        logger.warning(
            "Texto excede limite de %d caracteres; truncando para validacion (M-2).",
            _MAX_TEXT_LENGTH,
        )
        text = text[:_MAX_TEXT_LENGTH]
    text = "".join(
        c
        for c in unicodedata.normalize("NFKD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()
    text = text.translate(_LEET_TABLE)
    return re.sub(r"(.)\1{2,}", r"\1", text)


def _check_text(
    text: str,
    error: Exception,
    patterns: tuple[re.Pattern[str], ...],
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
        text,
        ContentNotAllowedError("Contenido no permitido.", text),
        _BLOCKED_PATTERNS,
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
