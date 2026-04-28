import pytest

from app.core.exceptions import ContentNotAllowedError, GeneratedContentBlockedError
from app.domain.content_guard import (
    check_document_content,
    check_generated_output,
    check_user_input,
)

# ---------------------------------------------------------------------------
# Baseline: clean inputs must not raise
# ---------------------------------------------------------------------------


def test_clean_input_passes():
    check_user_input("Tell me about Aragorn's backstory in Middle-earth.")


def test_clean_document_passes():
    check_document_content("Once upon a time in a land far away there lived a dragon.")


def test_clean_generated_passes():
    check_generated_output("The faction controls the northern trade routes.")


def test_empty_string_passes():
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
        "síntesis drogas ilegales",
        "esto es acoso directo",
        "harassment campaign",
    ],
)
def test_direct_keywords_blocked(text):
    with pytest.raises(ContentNotAllowedError):
        check_user_input(text)


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
        "ｈａｒａｓｓｍｅｎｔ",
    ],
)
def test_fullwidth_unicode_blocked(text):
    with pytest.raises(ContentNotAllowedError):
        check_user_input(text)


# ---------------------------------------------------------------------------
# Unicode normalization: combining diacritics / homoglyphs
# ---------------------------------------------------------------------------


def test_diacritic_porn_blocked():
    # p + o + r + n with combining accent — NFKD strips diacritics
    check_user_input.__module__  # ensure import
    with pytest.raises(ContentNotAllowedError):
        check_user_input("pórn video")  # ó with combining accent → o after NFKD


def test_superscript_digits_normalized():
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
        "HARASSMENT",
        "PoRn",
        "HaRaSSmeNt",
    ],
)
def test_mixed_case_blocked(text):
    with pytest.raises(ContentNotAllowedError):
        check_user_input(text)


# ---------------------------------------------------------------------------
# Function routing: check_document_content and check_generated_output
# ---------------------------------------------------------------------------


def test_document_content_raises_content_not_allowed():
    with pytest.raises(ContentNotAllowedError):
        check_document_content("explicit sexual material found")


def test_generated_output_raises_generated_content_blocked():
    with pytest.raises(GeneratedContentBlockedError):
        check_generated_output("this is porn content")


# ---------------------------------------------------------------------------
# Edge: whitespace-separated keywords should still match (regex \b handles it)
# ---------------------------------------------------------------------------


def test_keyword_with_surrounding_whitespace_blocked():
    with pytest.raises(ContentNotAllowedError):
        check_user_input("   porn   ")


def test_keyword_embedded_in_sentence_blocked():
    with pytest.raises(ContentNotAllowedError):
        check_user_input("I found some porn on the server")
