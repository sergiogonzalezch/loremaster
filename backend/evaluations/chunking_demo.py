# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Chunking Demo -- Loremaster
Comparativa: Fixed-Size (RecursiveCharacterTextSplitter) vs Semantic Chunking

Sin Qdrant ni LLM. Dependencias: langchain-text-splitters, sentence-transformers, numpy.
Todas ya estan en requirements.txt del backend.

Uso (desde backend/ con el venv activo):
    python evaluations/chunking_demo.py
"""

import io
import re
import sys

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

# Forzar UTF-8 en stdout para compatibilidad con Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --------------------------------------------------------------------------- #
# Texto de muestra
# --------------------------------------------------------------------------- #
# Worldbuilding en espanol con 5 secciones tematicas diferenciadas.
# El chunker semantico deberia detectar las 4 fronteras principales.

SAMPLE_TEXT = """
El Reino de Valdorath fue fundado hace tres siglos por el mago Arion el Plateado, quien
unifico las cinco tribus nomadas del continente de Aetheron bajo un unico estandarte.
Su reinado duro cuarenta anios y estuvo marcado por la construccion de la Gran Biblioteca
de Solmara, repositorio de todo el conocimiento arcano del mundo conocido. Tras su muerte,
sus tres hijos se disputaron el trono en la llamada Guerra de los Herederos, un conflicto
que duro doce anios y redujo a cenizas la mitad de las ciudades del norte. Fue el Tratado
de Piedra Negra el que puso fin a la guerra, dividiendo el reino en tres provincias
gobernadas por consejos regionales bajo la supervision de un rey arbitro.

Las tierras de Valdorath se extienden desde las Montanias de Greidur al norte hasta las
calidas playas del Mar de Ambar al sur. Al este, el Bosque Eterno de Sylvara cubre casi
un tercio del territorio y es hogar de los elfos del claro, seres inmortales que rara vez
interactuan con las otras razas. El rio Valdis atraviesa el corazon del continente desde
los glaciares del norte hasta su desembocadura en el Delta Dorado, donde se asienta la
ciudad mas prospera del reino: Puerto Aureo. En el centro del mapa destaca la Llanura de
las Cenizas, un vasto paramo donde antiguamente se libraban las grandes batallas y cuyo
suelo aun conserva vestigios de magia oscura de aquellos tiempos.

La Orden del Sol Naciente es la faccion religiosa mas poderosa, con templos en cada ciudad
importante y una guardia sagrada entrenada en combate y magia de luz. Los Mercaderes del
Gremio Libre controlan el comercio fluvial y tienen influencia directa sobre el Consejo de
Puerto Aureo, siendo capaces de movilizar ejercitos de mercenarios con solo pagar el precio
adecuado. En las sombras opera la Hermandad de la Mano Silenciosa, una red de espias y
asesinos que ningun noble se atreve a ignorar, pues sus metodos son tan efectivos como
impredecibles. Los Guardianes del Bosque velan por los intereses de Sylvara y con
frecuencia entran en conflicto con los colonos humanos que intentan talar sus arboles.

El sistema magico de Aetheron se basa en los llamados Nodos de Energia, puntos donde la
fuerza vital del mundo se concentra y puede ser canalizada por aquellos con el don innato.
Existen cinco tipos de magia reconocidos por la Gran Biblioteca: elemental, arcana, divina,
umbral y salvaje, cada una con sus propias reglas, limitaciones y efectos secundarios. El
uso excesivo de magia consume la vitalidad del practicante, un fenomeno conocido como el
Sangrado del Alma, que puede llevar a la locura o la muerte en casos extremos. Solo los
magos de alto rango conocen las tecnicas de mitigacion que permiten usar la magia durante
periodos prolongados sin sufrir danios permanentes.

Desde hace un anio, una plaga misteriosa esta convirtiendo en piedra a los animales y
plantas del Bosque Eterno, avanzando lentamente hacia los asentamientos humanos cercanos.
Los sabios de Solmara sospechan que alguien ha activado un Nodo Corrompido, una forma de
energia prohibida que los antiguos sellaron hace siglos bajo el Monte Helador. La Orden del
Sol Naciente culpa a los elfos de haber perturbado el equilibrio, mientras que los
Guardianes del Bosque senalan con el dedo a los experimentos arcanos del Gremio Libre. El
rey Aldric IV ha convocado a los representantes de todas las facciones a una cumbre en
Solmara para el dia del solsticio de verano, donde deberan acordar una respuesta conjunta
antes de que la plaga alcance las ciudades del interior.
""".strip()

# --------------------------------------------------------------------------- #
# Configuracion
# --------------------------------------------------------------------------- #

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

FIXED_CONFIGS = [
    {"chunk_size": 256, "chunk_overlap": 25},
    {"chunk_size": 512, "chunk_overlap": 50},
    {"chunk_size": 1024, "chunk_overlap": 100},
]

# Percentil de distancias coseno usado como umbral de corte semantico.
# Valores altos (90-95) => pocos chunks grandes.
# Valores bajos (60-70) => mas chunks pequenios.
SEMANTIC_THRESHOLD_PERCENTILE = 80.0

PREVIEW_LEN = 90
WIDTH = 80


# --------------------------------------------------------------------------- #
# Fixed-size chunking
# --------------------------------------------------------------------------- #


def fixed_size_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)


# --------------------------------------------------------------------------- #
# Semantic chunking
# --------------------------------------------------------------------------- #


def _split_into_sentences(text: str) -> list[str]:
    """Divide el texto en frases usando puntuacion final."""
    raw = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [s.strip() for s in raw if len(s.strip()) > 8]


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom < 1e-10:
        return 1.0
    return float(1.0 - np.dot(a, b) / denom)


def semantic_chunks(
    text: str,
    model: SentenceTransformer,
    threshold_percentile: float = 80.0,
    window_size: int = 1,
) -> tuple[list[str], list[float], float, list[int]]:
    """
    Chunking semantico inspirado en langchain_experimental.SemanticChunker.

    Pasos:
      1. Divide el texto en frases.
      2. Crea ventanas combinando frases vecinas (contexto).
      3. Embede cada ventana con sentence-transformers.
      4. Calcula distancia coseno entre ventanas consecutivas.
      5. Corta donde la distancia supera el percentil indicado.

    Returns:
        chunks          -- lista de strings resultantes
        distances       -- distancias coseno entre frases consecutivas (len = frases-1)
        threshold       -- valor de corte usado
        breakpoints     -- indices de frase donde se realizo el corte (1-based)
    """
    sentences = _split_into_sentences(text)
    if len(sentences) <= 1:
        return sentences, [], 0.0, []

    # Ventanas con contexto para embeddings mas estables
    windowed = []
    for i in range(len(sentences)):
        start = max(0, i - window_size)
        end = min(len(sentences), i + window_size + 1)
        windowed.append(" ".join(sentences[start:end]))

    embeddings = model.encode(
        windowed, show_progress_bar=False, normalize_embeddings=True
    )

    distances = [
        _cosine_distance(embeddings[i], embeddings[i + 1])
        for i in range(len(embeddings) - 1)
    ]

    threshold = float(np.percentile(distances, threshold_percentile))
    # breakpoints[i] = indice de la primera frase del chunk i+1
    breakpoints = [i + 1 for i, d in enumerate(distances) if d > threshold]

    # Construir chunks agrupando frases en los puntos de corte
    chunks, prev = [], 0
    for bp in breakpoints:
        chunk = " ".join(sentences[prev:bp]).strip()
        if chunk:
            chunks.append(chunk)
        prev = bp
    last = " ".join(sentences[prev:]).strip()
    if last:
        chunks.append(last)

    return chunks, distances, threshold, breakpoints


# --------------------------------------------------------------------------- #
# Helpers de salida
# --------------------------------------------------------------------------- #


def _sep(char: str = "=") -> None:
    print(char * WIDTH)


def _chunk_stats(chunks: list[str]) -> dict:
    sizes = [len(c) for c in chunks]
    return {
        "count": len(chunks),
        "avg": int(sum(sizes) / len(sizes)) if sizes else 0,
        "min": min(sizes) if sizes else 0,
        "max": max(sizes) if sizes else 0,
    }


def _print_fixed_chunks(chunks: list[str]) -> None:
    for i, chunk in enumerate(chunks):
        preview = chunk.replace("\n", " ")[:PREVIEW_LEN]
        if len(chunk) > PREVIEW_LEN:
            preview += "..."
        print(f"  #{i+1:02d} [{len(chunk):4d} ch]  {preview}")
    print()


def _print_semantic_chunks(
    chunks: list[str],
    distances: list[float],
    threshold: float,
    breakpoints: list[int],
) -> None:
    """
    Muestra cada chunk con la distancia coseno en la frontera que lo separa del siguiente.
    El indice de frontera corresponde a breakpoints[i]-1 en el array distances.
    """
    for i, chunk in enumerate(chunks):
        preview = chunk.replace("\n", " ")[:PREVIEW_LEN]
        if len(chunk) > PREVIEW_LEN:
            preview += "..."

        # Distancia en la frontera con el chunk siguiente
        boundary = ""
        if i < len(breakpoints):
            dist_idx = breakpoints[i] - 1
            if dist_idx < len(distances):
                d = distances[dist_idx]
                sim = 1.0 - d
                boundary = f"  [sim->sig: {sim:.3f} | dist: {d:.3f}]  <<< CORTE"

        print(f"  #{i+1:02d} [{len(chunk):4d} ch]{boundary}")
        print(f"       {preview}")
    print()


def _print_summary_table(results: list[tuple[str, dict]]) -> None:
    _sep("=")
    print(f"  {'Metodo':<26} | {'Chunks':>6} | {'Avg':>6} | {'Min':>6} | {'Max':>6}")
    print(f"  {'-'*26}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}")
    for name, s in results:
        print(
            f"  {name:<26} | {s['count']:>6} | {s['avg']:>6} | {s['min']:>6} | {s['max']:>6}"
        )
    _sep("=")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    text = SAMPLE_TEXT
    sentences = _split_into_sentences(text)

    _sep("=")
    print("  LOREMASTER -- CHUNKING DEMO")
    print("  Fixed-Size (RecursiveCharacterTextSplitter) vs Semantic Chunking")
    _sep("=")
    print(f"\n  Texto fuente : {len(text)} caracteres")
    print(f"  Frases aprox.: {len(sentences)}")
    print()

    all_results: list[tuple[str, dict]] = []

    # ── Fixed-size ──────────────────────────────────────────────────────────
    for cfg in FIXED_CONFIGS:
        cs = cfg["chunk_size"]
        co = cfg["chunk_overlap"]
        chunks = fixed_size_chunks(text, cs, co)
        s = _chunk_stats(chunks)
        label = f"Fixed {cs:>4}  (overlap={co:>3})"
        all_results.append((label, s))

        _sep("-")
        print(f"  FIXED-SIZE  |  chunk_size={cs}  overlap={co}")
        print(f"  Separadores: ['\\\\n\\\\n', '\\\\n', '. ', ' ', '']")
        _sep("-")
        _print_fixed_chunks(chunks)
        print(
            f"  RESUMEN: {s['count']} chunks  |"
            f"  avg={s['avg']}  min={s['min']}  max={s['max']}"
        )
        print()

    # ── Semantic ────────────────────────────────────────────────────────────
    _sep("-")
    print(f"  SEMANTIC  |  modelo={EMBEDDING_MODEL}")
    print(
        f"  Metodo: ventana deslizante + distancia coseno"
        f"  |  umbral=p{int(SEMANTIC_THRESHOLD_PERCENTILE)}"
    )
    _sep("-")
    print("  Cargando modelo de embeddings...", end=" ", flush=True)
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("listo.\n")

    chunks, distances, threshold, breakpoints = semantic_chunks(
        text, model, threshold_percentile=SEMANTIC_THRESHOLD_PERCENTILE
    )
    s = _chunk_stats(chunks)
    label = f"Semantic (p{int(SEMANTIC_THRESHOLD_PERCENTILE)})"
    all_results.append((label, s))

    if distances:
        print(
            f"  Distancias coseno -- "
            f"min={min(distances):.3f}  "
            f"max={max(distances):.3f}  "
            f"umbral(p{int(SEMANTIC_THRESHOLD_PERCENTILE)})={threshold:.3f}"
        )
        print(f"  Puntos de corte detectados: {len(breakpoints)}\n")

    _print_semantic_chunks(chunks, distances, threshold, breakpoints)
    print(
        f"  RESUMEN: {s['count']} chunks  |"
        f"  avg={s['avg']}  min={s['min']}  max={s['max']}"
    )
    print()

    # ── Tabla resumen ────────────────────────────────────────────────────────
    print()
    _print_summary_table(all_results)

    print()
    print("  NOTAS:")
    print("  * Fixed-size: cortes mecanicos cada N chars. Rapido, predecible.")
    print("    Puede partir oraciones o ideas a la mitad. El overlap compensa")
    print("    la perdida de contexto en fronteras de chunk.")
    print()
    print("  * Semantic:   cortes donde la similitud entre frases cae mas de lo")
    print(
        f"    normal (percentil {int(SEMANTIC_THRESHOLD_PERCENTILE)} configurable). Mas lento (requiere embeddings)."
    )
    print("    Produce chunks tematicamente coherentes y de tamano variable.")
    print()
    print("  * Para RAG: semantic mejora el retrieval en textos con secciones")
    print("    tematicas claras. Fixed-size es suficiente para textos homogeneos")
    print("    o cuando la velocidad de ingesta es prioritaria.")
    print()


if __name__ == "__main__":
    main()
