import re

from app.core.exceptions import ContentNotAllowedError, GeneratedContentBlockedError

_BLOCKED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(porn|porno|xxx|explicit\s+sexual|sexo\s+expl[íi]cito)\b", re.I),
    re.compile(r"\b(hate\s+speech|supremac(?:y|ista)|genocid(?:e|io)|slur)\b", re.I),
    re.compile(
        r"\b(make|build|fabricar|crear)\s+((a|an|un|una)\s+)?(bomb|bomba|weapon|arma)\b",
        re.I,
    ),
    re.compile(
        r"\b(synthesize|s[íi]ntesis|fabricar|cocinar)\s+(drugs?|drogas?|meth)\b",
        re.I,
    ),
    re.compile(
        r"\b(acoso|harass(?:ment)?|denigrate|denigrar|humill(?:ar|ation))\b",
        re.I,
    ),
)


def _check_text(text: str, error: Exception) -> None:
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(text):
            raise error


def check_user_input(text: str) -> None:
    """Raises ContentNotAllowedError if text contains blocked content."""
    _check_text(text, ContentNotAllowedError("Contenido no permitido."))


def check_document_content(text: str) -> None:
    """Raises ContentNotAllowedError if extracted document text contains blocked content."""
    _check_text(
        text, ContentNotAllowedError("El documento contiene contenido no permitido.")
    )


def check_generated_output(text: str) -> None:
    """Raises GeneratedContentBlockedError if LLM output contains blocked content."""
    _check_text(text, GeneratedContentBlockedError())
