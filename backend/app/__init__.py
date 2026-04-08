from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_pycache_prefix() -> None:
    """
    Centraliza los archivos .pyc del proyecto en backend/.pycache.

    Se ejecuta al importar el paquete `app` (por ejemplo, al correr
    `uvicorn app.main:app --reload` o en contenedores Docker con el mismo
    entrypoint).
    """
    if sys.pycache_prefix:
        return

    env_prefix = os.getenv("PYTHONPYCACHEPREFIX")
    if env_prefix:
        target = Path(env_prefix).resolve()
    else:
        target = Path(__file__).resolve().parents[1] / ".pycache"

    target.mkdir(parents=True, exist_ok=True)
    sys.pycache_prefix = str(target)


_configure_pycache_prefix()
