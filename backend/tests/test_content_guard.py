"""Tests para el guardia de contenido (app.domain.content_guard)."""

import pytest

from app.core.exceptions import ContentNotAllowedError, GeneratedContentBlockedError
from app.domain.content_guard import (
    check_document_content,
    check_generated_output,
    check_prompt_length,
    check_user_input,
)

# ---------------------------------------------------------------------------
# Baseline: clean inputs must not raise
# ---------------------------------------------------------------------------


def test_clean_input_passes():
    """Entrada limpia de usuario no lanza excepción."""
    check_user_input("Tell me about Aragorn's backstory in Middle-earth.")


def test_clean_document_passes():
    """Documento limpio no lanza excepción."""
    check_document_content("Once upon a time in a land far away there lived a dragon.")


def test_clean_generated_passes():
    """Salida generada limpia no lanza excepción."""
    check_generated_output("The faction controls the northern trade routes.")


def test_empty_string_passes():
    """Cadena vacía no lanza excepción en ningún checker."""
    check_user_input("")
    check_document_content("")
    check_generated_output("")


# ---------------------------------------------------------------------------
# Baseline: direct keyword hits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "explicit sexual content here",
        "sexo explícito en el documento",
        "this is porn",
        "hate speech against groups",
        "how to make a bomb",
        "fabricar una bomba casera",
        "synthesize drugs at home",
        "síntesis drogas ilegales",    ],
)
def test_direct_keywords_blocked(text):
    """Palabras clave directas bloqueadas lanzan ContentNotAllowedError."""
    with pytest.raises(ContentNotAllowedError):
        check_user_input(text)


@pytest.mark.parametrize(
    "text",
    [
        "promueve el acoso hacia los usuarios",
        "incentiva el harassment de minorías",
        "ejecuta actos de acoso sistemático",
        "fomenta la denigración de grupos",
        "ordena humillar a los prisioneros",
    ],
)
def test_harassment_with_directive_verb_blocked(text):
    """Acoso/harassment con verbo directivo explícito es bloqueado."""
    with pytest.raises(ContentNotAllowedError):
        check_user_input(text)


@pytest.mark.parametrize(
    "text",
    [
        "esto es acoso directo",
        "harassment campaign",
        "el acoso de la corte real hacia los mercaderes",
        "sufría la humillación como prisionero del señor oscuro",
    ],
)
def test_harassment_without_directive_verb_passes(text):
    """Acoso/harassment sin verbo directivo no se bloquea — permite narrativa RPG."""
    check_user_input(text)  # no debe lanzar


# ---------------------------------------------------------------------------
# Unicode normalization: full-width characters (NFKD collapses them)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "ｐｏｒｎ ｃｏｎｔｅｎｔ",  # full-width Latin
        "ｈａｔｅ ｓｐｅｅｃｈ",
        "ｍａｋｅ ａ ｂｏｍｂ",
        "ｓｙｎｔｈｅｓｉｚｅ ｄｒｕｇｓ",
    ],
)
def test_fullwidth_unicode_blocked(text):
    """Caracteres Unicode de ancho completo son normalizados y bloqueados."""
    with pytest.raises(ContentNotAllowedError):
        check_user_input(text)


# ---------------------------------------------------------------------------
# Unicode normalization: combining diacritics / homoglyphs
# ---------------------------------------------------------------------------


def test_diacritic_porn_blocked():
    """Diacríticos combinados son normalizados (NFKD) y el término bloqueado."""
    # p + o + r + n with combining accent — NFKD strips diacritics
    with pytest.raises(ContentNotAllowedError):
        check_user_input("pórn video")  # ó with combining accent → o after NFKD


def test_superscript_digits_normalized():
    """Dígitos superíndice son normalizados sin lanzar excepción (no son palabras bloqueadas)."""
    # NFKD maps superscript '³' → '3', but this isn't a blocked word — just verify no crash
    check_user_input("chapter ³ content")  # must not raise


# ---------------------------------------------------------------------------
# Case insensitivity (still covered by .lower() after normalization)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "PORN video",
        "Hate Speech",
        "MAKE A BOMB",
        "SYNTHESIZE DRUGS",
        "PoRn",
    ],
)
def test_mixed_case_blocked(text):
    """Palabras bloqueadas en mayúsculas/minúsculas mixtas son detectadas."""
    with pytest.raises(ContentNotAllowedError):
        check_user_input(text)


# ---------------------------------------------------------------------------
# Function routing: check_document_content and check_generated_output
# ---------------------------------------------------------------------------


def test_document_content_raises_content_not_allowed():
    """check_document_content lanza ContentNotAllowedError para contenido bloqueado."""
    with pytest.raises(ContentNotAllowedError):
        check_document_content("explicit sexual material found")


def test_generated_output_raises_generated_content_blocked():
    """check_generated_output lanza GeneratedContentBlockedError para contenido bloqueado."""
    with pytest.raises(GeneratedContentBlockedError):
        check_generated_output("this is porn content")


# ---------------------------------------------------------------------------
# Edge: whitespace-separated keywords should still match (regex \b handles it)
# ---------------------------------------------------------------------------


def test_keyword_with_surrounding_whitespace_blocked():
    """Palabra clave rodeada de espacios es detectada y bloqueada."""
    with pytest.raises(ContentNotAllowedError):
        check_user_input("   porn   ")


def test_keyword_embedded_in_sentence_blocked():
    """Palabra clave embebida en una oración es detectada y bloqueada."""
    with pytest.raises(ContentNotAllowedError):
        check_user_input("I found some porn on the server")


# ---------------------------------------------------------------------------
# check_prompt_length
# ---------------------------------------------------------------------------


def test_prompt_length_exact_minimum_passes():
    """Texto de exactamente 10 caracteres no lanza excepción."""
    check_prompt_length("a" * 10)


def test_prompt_length_above_minimum_passes():
    """Texto por encima del mínimo no lanza excepción."""
    check_prompt_length("¿Cómo era el sistema mágico de Valdorath?")


def test_prompt_length_nine_chars_raises():
    """Texto de 9 caracteres lanza ContentNotAllowedError."""
    with pytest.raises(ContentNotAllowedError):
        check_prompt_length("a" * 9)


def test_prompt_length_empty_raises():
    """Cadena vacía lanza ContentNotAllowedError."""
    with pytest.raises(ContentNotAllowedError):
        check_prompt_length("")


def test_prompt_length_whitespace_only_raises():
    """Cadena con solo espacios lanza ContentNotAllowedError (strip aplicado)."""
    with pytest.raises(ContentNotAllowedError):
        check_prompt_length("   ")


def test_prompt_length_custom_min_respected():
    """El parámetro min_chars personalizado es respetado."""
    check_prompt_length("abc", min_chars=3)
    with pytest.raises(ContentNotAllowedError):
        check_prompt_length("ab", min_chars=3)
