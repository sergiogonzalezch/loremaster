"""Capa semántica de moderación usando Llama Guard 3 via Ollama.

Fail-open: si el guard no responde (timeout, error de conexión, parseo
inesperado), se registra un warning y el texto pasa sin bloquear.
El sistema no debe degradarse por indisponibilidad del guard.

Activar con LLAMA_GUARD_ENABLED=true en .env.
"""

import logging

import httpx

from app.core.config import settings
from app.core.exceptions import GeneratedContentBlockedError

logger = logging.getLogger(__name__)

_UNSAFE_CATEGORIES = (
    "S1: Violent Crimes.\n"
    "S2: Non-Violent Crimes.\n"
    "S3: Sex Crimes.\n"
    "S4: Child Exploitation.\n"
    "S5: Defamation.\n"
    "S6: Specialized Advice.\n"
    "S7: Privacy.\n"
    "S8: Intellectual Property.\n"
    "S9: Indiscriminate Weapons.\n"
    "S10: Hate.\n"
    "S11: Self-Harm.\n"
    "S12: Sexual Content.\n"
    "S13: Elections."
)


def _build_guard_prompt(user_query: str, agent_response: str) -> str:
    """Construye el prompt en el formato exacto requerido por Llama Guard 3."""
    return (
        "<|start_header_id|>user<|end_header_id|>\n\n"
        "Task: Check if there is unsafe content in 'Agent' messages in conversations "
        "according our safety policy with the below categories.\n\n"
        f"<BEGIN UNSAFE CONTENT CATEGORIES>\n{_UNSAFE_CATEGORIES}\n<END UNSAFE CONTENT CATEGORIES>\n\n"
        "<BEGIN CONVERSATION>\n\n"
        f"User: {user_query}\n\n"
        f"Agent: {agent_response}\n\n"
        "<END CONVERSATION>\n\n"
        "Provide your safety assessment for ONLY THE LAST 'Agent' turn in the above conversation:\n"
        " - First line must read 'safe' or 'unsafe'.\n"
        " - If unsafe, a second line must include a comma-separated list of violated categories.\n"
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
    )


async def check_with_llama_guard(user_query: str, agent_response: str) -> None:
    """Verifica la respuesta del LLM contra Llama Guard 3 via Ollama.

    No hace nada si LLAMA_GUARD_ENABLED=false.

    Fail-open: en timeout, error de red o parseo inesperado, registra un
    warning y retorna sin bloquear.

    Args:
        user_query: Prompt original del usuario (contexto para el guard).
        agent_response: Texto generado por el LLM a verificar.

    Raises:
        GeneratedContentBlockedError: si el guard clasifica la respuesta como unsafe.

    """
    if not settings.llama_guard_enabled:
        return

    prompt = _build_guard_prompt(user_query, agent_response)
    payload = {
        "model": settings.llama_guard_model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json=payload,
                timeout=settings.llama_guard_timeout,
            )
            resp.raise_for_status()
            verdict = resp.json().get("response", "").strip().lower()
    except httpx.TimeoutException:
        logger.warning(
            "Llama Guard timeout (%.1fs) — fail-open, response passed",
            settings.llama_guard_timeout,
        )
        return
    except Exception:  # noqa: BLE001
        logger.warning("Llama Guard unavailable — fail-open, response passed", exc_info=True)
        return

    if verdict.startswith("unsafe"):
        categories = verdict.split("\n")[1].strip() if "\n" in verdict else ""
        logger.warning("Llama Guard blocked response — categories: %s", categories or "unknown")
        raise GeneratedContentBlockedError(agent_response[:200])

    logger.debug("Llama Guard verdict: safe")
