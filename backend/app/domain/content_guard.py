import re
import unicodedata

from app.core.exceptions import ContentNotAllowedError, GeneratedContentBlockedError

# Patterns applied to user input and documents: block any mention of harmful actions.
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

# Patterns applied to LLM output: weapon/bomb require explicit instructional framing
# to avoid false positives when narrative fantasy content mentions weapons in context.
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


def _normalize(text: str) -> str:
    # NFKD decomposes ligatures/full-width chars; stripping Mn removes combining
    # diacritics so that é→e, ó→o, etc., enabling accent-insensitive matching.
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()


def _check_text(
    text: str, error: Exception, patterns: tuple[re.Pattern[str], ...]
) -> None:
    normalized = _normalize(text)
    for pattern in patterns:
        if pattern.search(normalized):
            raise error


def check_user_input(text: str) -> None:
    """Raises ContentNotAllowedError if text contains blocked content."""
    _check_text(
        text, ContentNotAllowedError("Contenido no permitido.", text), _BLOCKED_PATTERNS
    )


def check_document_content(text: str) -> None:
    """Raises ContentNotAllowedError if extracted document text contains blocked content."""
    _check_text(
        text,
        ContentNotAllowedError("El documento contiene contenido no permitido.", text),
        _BLOCKED_PATTERNS,
    )


def check_generated_output(text: str) -> None:
    """Raises GeneratedContentBlockedError if LLM output contains blocked content."""
    _check_text(text, GeneratedContentBlockedError(text), _OUTPUT_BLOCKED_PATTERNS)
