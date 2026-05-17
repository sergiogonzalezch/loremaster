"""Guardia de contenido: validación de entrada de usuarios, documentos y salida del LLM.

Aplica patrones de expresiones regulares para detectar contenido no permitido
antes de procesarlo o tras generarlo.

LIMITACIONES CONOCIDAS:
- Este modulo es una primera linea de defensa, no una barrera exhaustiva.
- No detecta: jailbreaks estructurales, leetspeak (e.g. "b0mb"), base64, ROT13,
  inyeccion de prompts via delimitadores, o tecnicas de evasion avanzadas.
- Requiere complemento con: validacion de esquemas de salida, rate limiting,
  monitoreo de comportamiento anomalo, y revision humana para casos criticos.

MITIGACION ReDoS:
- Se aplica limite de longitud (100KB) antes de normalizar con NFKD.
- Texto que exceda el limite se trunca para evitar bloqueo del worker.
"""

import logging
import re
import unicodedata

from app.core.exceptions import ContentNotAllowedError, GeneratedContentBlockedError

logger = logging.getLogger(__name__)

# Sustituciones leetspeak comunes para evasión de filtros
# Base:    0→o, 1→i, 3→e, 4→a, 5→s, 6→g, @→a, $→s
# Fix #6:  7→t, 8→b, +→t  (| omitido — demasiados FP en pipes de código/markdown)
_LEET_TABLE = str.maketrans("013456@$78+", "oieasgastbt")

# Limite de longitud para prevenir ReDoS/CPU-DoS
_MAX_TEXT_LENGTH = 100_000  # 100 KB

# Longitud mínima para prompts enviados al LLM
_MIN_PROMPT_LENGTH = 10

# Patrones aplicados a entrada de usuarios y documentos: bloquean cualquier mención de acciones dañinas.
_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(porn|porno|xxx|explicit\s+sexual|sexo\s+expl[íi]cito)\b",
        re.IGNORECASE,
    ),
    # supremacia cubre la forma nominal "supremacía" tras normalización NFKD (ía→ia)
    re.compile(
        r"\b(hate\s+speech|supremac(?:y|ista|ia)|slur)\b",
        re.IGNORECASE,
    ),
    # genocidio solo con intención instructiva — "perpetró un genocidio" pasa; "cómo ejecutar un genocidio" bloquea
    re.compile(
        r"\b(como|instrucciones?\s+para|ejecutar?|planear?|organizar?|fomentar?|incitar?)\s+.{0,25}genocid(?:e|io)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(make|build|fabricar|crear|hacer)\s+((a|an|un|una)\s+)?(bomb|bomba|weapon|arma)\b",
        re.IGNORECASE,
    ),
    # metanfetamina añadido — antes solo "meth" (inglés) estaba cubierto
    re.compile(
        r"\b(synthesize|sintetizar|s[íi]ntesis|fabricar|cocinar)\s+(drugs?|drogas?|meth|metanfetamina|methamphetamine)\b",
        re.IGNORECASE,
    ),
    # acoso/humillación requieren verbo directivo — permite narrativa RPG ("sufría el acoso", "la humillación del prisionero")
    # humillacion cubre la forma sustantiva "humillación" tras normalización NFKD
    re.compile(
        r"\b(promueve|incentiva|practica|ejecuta|fomenta|realiza|incita|ordena)\s+.{0,25}(acoso|harass(?:ment)?|denigra(?:r|cion)?|denigrate|humill(?:ar|acion))\b",
        re.IGNORECASE,
    ),
    # BYP-L05 — noun+noun: "terrorist bomb instructions" no contiene verbo antes de "bomb"
    re.compile(r"\b(bomb|bomba)\s+(instructions?|steps?|tutorial|guide|recipe)\b", re.IGNORECASE),
    # Fix #4 option C — pares estrechos FR/DE/IT (cubren BYP-M01/M02/M03)
    re.compile(r"\b(fabriquer|construire)\s+(une?\s+)?bombe?\b", re.IGNORECASE),
    re.compile(r"\bbaue?n?\s+.{0,20}bombe?\b", re.IGNORECASE),
    re.compile(r"\bsintetizz\w+\s+.{0,25}metanfetamina\b", re.IGNORECASE),
)
"""Patrones para bloquear contenido en entrada de usuarios y documentos."""

# Patrones aplicados a salida del LLM: arma/bomba y humillación requieren enmarcado instructivo
# para evitar falsos positivos cuando el LLM narra contenido RPG legítimo.
_OUTPUT_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(porn|porno|xxx|explicit\s+sexual|sexo\s+expl[íi]cito)\b",
        re.IGNORECASE,
    ),
    # supremacia cubre "supremacía" (nominal) tras NFKD — cerraba FN con mistral (HARM-10)
    re.compile(
        r"\b(hate\s+speech|supremac(?:y|ista|ia)|slur)\b",
        re.IGNORECASE,
    ),
    # genocidio solo con intención instructiva — permite al LLM narrar "la facción perpetró un genocidio"
    re.compile(
        r"\b(como|instrucciones?\s+para|ejecutar?|planear?|organizar?|fomentar?|incitar?)\s+.{0,25}genocid(?:e|io)\b",
        re.IGNORECASE,
    ),
    # how to añadido — cubre output tipo "how to build a bomb"; hacer/construir amplían verbo
    re.compile(
        r"\b(c[oó]mo|how\s+to|instrucciones?)\s+(para\s+)?(make|build|fabricar|crear|hacer|construir)\s+((a|an|un|una)\s+)?(bomb|bomba|weapons?|armas?)\b",
        re.IGNORECASE,
    ),
    # gap .{0,40} — cubre "synthesis process for methamphetamine" (palabras entre verbo y sustantivo)
    # preparar/producir añadidos para cubrir variantes de producción
    re.compile(
        r"\b(synthesize|synthesis|sintetizar|s[íi]ntesis|fabricar|cocinar|preparar|producir)\s+.{0,40}\b(drugs?|drogas?|meth|metanfetamina|methamphetamine)\b",
        re.IGNORECASE,
    ),
    # acoso/humillación requieren verbo directivo — permite al LLM narrar villanos que usan humillación
    # humillacion cubre "humillación" (sustantivo) tras normalización NFKD — cerraba FP con llama3.2 (RPG-FP03)
    re.compile(
        r"\b(promueve|incentiva|practica|ejecuta|fomenta|realiza|incita|ordena)\s+.{0,25}(acoso|harass(?:ment)?|denigra(?:r|cion)?|denigrate|humill(?:ar|acion))\b",
        re.IGNORECASE,
    ),
    # BYP-L05 y Fix #4 en output: mismos patrones que input
    re.compile(r"\b(bomb|bomba)\s+(instructions?|steps?|tutorial|guide|recipe)\b", re.IGNORECASE),
    re.compile(r"\b(fabriquer|construire)\s+(une?\s+)?bombe?\b", re.IGNORECASE),
    re.compile(r"\bbaue?n?\s+.{0,20}bombe?\b", re.IGNORECASE),
    re.compile(r"\bsintetizz\w+\s+.{0,25}metanfetamina\b", re.IGNORECASE),
)
"""Patrones para bloquear contenido en salida generada por el LLM."""


def _normalize(text: str) -> str:
    """Normaliza texto para comparación robusta contra evasiones comunes.

    Pasos:
    1. Trunca a _MAX_TEXT_LENGTH para prevenir ReDoS.
    2. NFKD + elimina diacríticos: é→e, ó→o, caracteres de ancho completo.
    3. Lowercase.
    4. Fix #5 — elimina separadores intercalados entre letras: b.o.m.b→bomb, b-o-m-b→bomb.
       Lookahead/lookbehind evita colapsar separadores legítimos en frases normales.
    5. Sustituye leetspeak (_LEET_TABLE): 0→o, 1→i, 3→e, @→a, $→s, 7→t, 8→b, +→t.
    6. Colapsa chars repetidos (bbooommmb→bomb) para evadir filtros por repetición.
    """
    if len(text) > _MAX_TEXT_LENGTH:
        logger.warning(
            "Texto excede limite de %d caracteres; truncando para validacion.",
            _MAX_TEXT_LENGTH,
        )
        text = text[:_MAX_TEXT_LENGTH]
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if unicodedata.category(c) != "Mn").lower()
    text = re.sub(r"(?<=[a-z0-9])[.\-_/\\](?=[a-z0-9])", "", text)
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
            error.pattern = pattern.pattern  # para auditoría en ModerationLog
            raise error


def check_prompt_length(text: str, min_chars: int = _MIN_PROMPT_LENGTH) -> None:
    """Verifica que el prompt tenga la longitud mínima requerida.

    Lanza ContentNotAllowedError si el texto es demasiado corto.
    """
    if len(text.strip()) < min_chars:
        msg = f"El prompt debe tener al menos {min_chars} caracteres."
        raise ContentNotAllowedError(msg, text)


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
