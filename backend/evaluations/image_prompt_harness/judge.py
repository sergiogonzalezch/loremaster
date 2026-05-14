"""Funciones de evaluación programática para el image prompt harness.

Evalúa dos criterios sobre el output de build_combined_prompt():
- Tipo correcto: el primer token coincide con el tipo de entidad esperado.
- En inglés: el output no contiene tokens función en español.
"""

# Palabras función españolas que no aparecen como tokens en listas visuales en inglés.
# Se comparan contra tokens individuales (split por coma y espacio) para evitar
# falsos positivos con substrings (e.g. "del" dentro de "model" no se matchea).
_SPANISH_TOKENS = frozenset({
    "el", "la", "los", "las", "una", "unos", "unas",
    "del", "con", "por", "para", "que", "como",
    "son", "está", "están", "tiene", "tienen", "lleva", "llevan",
    "su", "sus", "también", "además", "pero", "sino",
    # Colores en español — los más probables en un prompt visual
    "negro", "negra", "blanco", "blanca", "rojo", "roja",
    "azul", "verde", "dorado", "dorada", "plateado", "plateada",
    "oscuro", "oscura", "claro", "clara",
    # Adjetivos físicos comunes en español
    "grande", "pequeño", "pequeña", "alto", "alta", "largo", "larga",
})


def check_tipo(output: str, expected_types: list[str]) -> bool:
    """Verifica que el primer token del output coincida con algún tipo esperado.

    El primer elemento de la lista comma-separated debe ser el tipo específico
    de la entidad (human, dragon, city, sword...).
    """
    if not output or not output.strip():
        return False
    first_token = output.split(",")[0].strip().lower()
    return first_token in {t.lower() for t in expected_types}


def check_english(output: str) -> bool:
    """Verifica que el output esté en inglés mediante heurístico de tokens españoles.

    Retorna False si algún token de la salida coincide exactamente con una
    palabra función o color español conocido.
    """
    if not output or not output.strip():
        return False
    tokens = {
        word.strip().lower().rstrip(".,;:")
        for segment in output.split(",")
        for word in segment.split()
    }
    return not tokens.intersection(_SPANISH_TOKENS)
