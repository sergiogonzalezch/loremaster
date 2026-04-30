# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Threshold Evaluation -- Loremaster
Evalúa el parámetro rag_score_threshold (similitud coseno) en los valores: 0.0, 0.3, 0.5, 0.7

Simula el comportamiento de Qdrant sin necesitar el servidor en marcha.
Usa sentence-transformers + numpy para calcular similitud coseno directamente.
Dependencias: sentence-transformers, numpy, langchain-text-splitters (todas en requirements.txt)

Uso (desde backend/ con el venv activo):
    python evaluations/threshold_eval.py
"""

import io
import sys

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --------------------------------------------------------------------------- #
# Texto de muestra  (mismo corpus que chunking_demo.py)
# --------------------------------------------------------------------------- #

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
# Consultas de prueba
# --------------------------------------------------------------------------- #
# Mezcla de consultas: on-topic específicas, on-topic amplias y off-topic
# para observar cómo cada umbral afecta recall y precision.

QUERIES = [
    {
        "id": "Q-01",
        "label": "Historia del reino (on-topic específica)",
        "text": "¿Quién fundó el Reino de Valdorath y cómo terminó la guerra de los herederos?",
        "expect_context": True,
    },
    {
        "id": "Q-02",
        "label": "Geografía (on-topic específica)",
        "text": "¿Dónde está el Bosque Eterno de Sylvara y qué razas lo habitan?",
        "expect_context": True,
    },
    {
        "id": "Q-03",
        "label": "Facciones (on-topic específica)",
        "text": "Describe las principales facciones políticas y religiosas del reino",
        "expect_context": True,
    },
    {
        "id": "Q-04",
        "label": "Sistema mágico (on-topic específica)",
        "text": "¿Qué es el Sangrado del Alma y cuáles son los tipos de magia?",
        "expect_context": True,
    },
    {
        "id": "Q-05",
        "label": "Plaga actual (on-topic específica)",
        "text": "¿Qué está causando la plaga que convierte en piedra el bosque?",
        "expect_context": True,
    },
    {
        "id": "Q-06",
        "label": "Consulta amplia (on-topic general)",
        "text": "Cuéntame sobre el mundo de fantasía",
        "expect_context": True,
    },
    {
        "id": "Q-07",
        "label": "Off-topic sin relación alguna",
        "text": "¿Cuántos pianistas profesionales hay actualmente en el mundo?",
        "expect_context": False,
    },
    {
        "id": "Q-08",
        "label": "Off-topic tecnología moderna",
        "text": "¿Cómo funciona el aprendizaje automático con redes neuronales?",
        "expect_context": False,
    },
]

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOP_K = 4
THRESHOLDS = [0.0, 0.3, 0.5, 0.7]

WIDTH = 90


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #


def _sep(char: str = "=", width: int = WIDTH) -> None:
    print(char * width)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom < 1e-10:
        return 0.0
    return float(np.dot(a, b) / denom)


def build_index(text: str, model: SentenceTransformer) -> tuple[list[str], np.ndarray]:
    """Chunking fijo (igual que producción) + embedding de cada chunk."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    embeddings = model.encode(
        chunks, show_progress_bar=False, normalize_embeddings=True
    )
    return chunks, embeddings


def search(
    query_vec: np.ndarray,
    chunk_embeddings: np.ndarray,
    chunks: list[str],
    top_k: int,
    score_threshold: float,
) -> list[tuple[float, str]]:
    """Replica el comportamiento de Qdrant search_context con score_threshold."""
    scores = [_cosine_sim(query_vec, emb) for emb in chunk_embeddings]
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    effective_threshold = score_threshold if score_threshold > 0.0 else None
    results = []
    for idx, score in ranked:
        if effective_threshold is None or score >= effective_threshold:
            results.append((score, chunks[idx]))
    return results


# --------------------------------------------------------------------------- #
# Resultados por consulta y umbral
# --------------------------------------------------------------------------- #


def run_evaluation(
    queries: list[dict],
    chunks: list[str],
    chunk_embeddings: np.ndarray,
    model: SentenceTransformer,
) -> list[dict]:
    """Devuelve una fila de métricas por cada (query, threshold)."""
    rows = []
    query_embeddings = model.encode(
        [q["text"] for q in queries],
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    for qi, query in enumerate(queries):
        q_vec = query_embeddings[qi]
        for thr in THRESHOLDS:
            hits = search(q_vec, chunk_embeddings, chunks, TOP_K, thr)
            scores = [s for s, _ in hits]
            rows.append(
                {
                    "query_id": query["id"],
                    "query_label": query["label"],
                    "threshold": thr,
                    "hits": len(hits),
                    "max_score": max(scores) if scores else 0.0,
                    "avg_score": sum(scores) / len(scores) if scores else 0.0,
                    "has_context": len(hits) > 0,
                    "expect_context": query["expect_context"],
                    "correct": (len(hits) > 0) == query["expect_context"],
                }
            )
    return rows


# --------------------------------------------------------------------------- #
# Impresión de resultados
# --------------------------------------------------------------------------- #


def _print_query_block(query: dict, rows_for_query: list[dict]) -> None:
    q = rows_for_query[0]
    expected = "SI" if query["expect_context"] else "NO"
    _sep("-")
    print(f"  {query['id']}  {query['label']}")
    print(f"  Consulta  : \"{query['text']}\"")
    print(f"  Esperado  : contexto={expected}")
    print()
    print(
        f"  {'Umbral':>7} | {'Chunks':>6} | {'Max sim':>8} | {'Avg sim':>8} | "
        f"{'Contexto':>9} | {'Correcto':>9}"
    )
    print(f"  {'-'*7}-+-{'-'*6}-+-{'-'*8}-+-{'-'*8}-+-{'-'*9}-+-{'-'*9}")
    for row in rows_for_query:
        ctx = "SI " if row["has_context"] else "NO "
        ok = "OK " if row["correct"] else "FALLO"
        print(
            f"  {row['threshold']:>7.1f} | {row['hits']:>6} | {row['max_score']:>8.3f} | "
            f"{row['avg_score']:>8.3f} | {ctx:>9} | {ok:>9}"
        )
    print()


def _print_threshold_summary(rows: list[dict]) -> None:
    """Tabla final: por threshold — precision media, recall, fallos."""
    _sep("=")
    print("  RESUMEN POR UMBRAL")
    print(
        "  Precision media: avg score de los chunks recuperados (más alto = mayor calidad)"
    )
    print(
        "  Recall medio   : chunks recuperados / top_k posibles (más alto = más cobertura)"
    )
    print("  Fallos         : consultas donde el resultado no coincide con lo esperado")
    _sep("-")
    print(
        f"  {'Umbral':>7} | {'Prec media':>10} | {'Recall medio':>13} | "
        f"{'Chunks/query':>13} | {'Fallos':>7}"
    )
    print(f"  {'-'*7}-+-{'-'*10}-+-{'-'*13}-+-{'-'*13}-+-{'-'*7}")
    for thr in THRESHOLDS:
        thr_rows = [r for r in rows if r["threshold"] == thr]
        prec_vals = [r["avg_score"] for r in thr_rows if r["hits"] > 0]
        recall_vals = [r["hits"] / TOP_K for r in thr_rows]
        fallos = sum(1 for r in thr_rows if not r["correct"])
        prec = sum(prec_vals) / len(prec_vals) if prec_vals else 0.0
        recall = sum(recall_vals) / len(recall_vals)
        avg_chunks = sum(r["hits"] for r in thr_rows) / len(thr_rows)
        print(
            f"  {thr:>7.1f} | {prec:>10.3f} | {recall:>13.3f} | "
            f"{avg_chunks:>13.1f} | {fallos:>7}"
        )
    _sep("=")


def _print_recommendation(rows: list[dict]) -> None:
    print()
    print("  INTERPRETACION")
    print()
    print("  score_threshold en Qdrant filtra resultados por similitud coseno.")
    print("  Un chunk solo se incluye en el contexto RAG si su score >= threshold.")
    print()
    print("  0.0  -> sin filtro; todos los top-k chunks pasan siempre.")
    print("         Maximiza contexto pero puede introducir ruido irrelevante.")
    print()
    print("  0.3  -> filtro suave (valor por defecto del proyecto).")
    print("         Descarta chunks muy poco relacionados. Equilibrio recall/ruido.")
    print()
    print("  0.5  -> filtro moderado.")
    print("         Solo chunks con similitud media-alta. Puede perder contexto")
    print("         en consultas amplias o corpus pequeños.")
    print()
    print("  0.7  -> filtro estricto.")
    print("         Exige alta similitud semántica. Riesgo alto de no encontrar")
    print("         contexto (NoContextAvailableError) en consultas generales.")
    print()
    # Recomendar basándonos en los datos
    best_thr = None
    best_score = -1.0
    for thr in THRESHOLDS:
        thr_rows = [r for r in rows if r["threshold"] == thr]
        fallos = sum(1 for r in thr_rows if not r["correct"])
        recall_vals = [r["hits"] / TOP_K for r in thr_rows]
        prec_vals = [r["avg_score"] for r in thr_rows if r["hits"] > 0]
        recall = sum(recall_vals) / len(recall_vals)
        prec = sum(prec_vals) / len(prec_vals) if prec_vals else 0.0
        # Combinación heurística: maximizar precision * recall y minimizar fallos
        score = prec * recall - fallos * 0.15
        if score > best_score:
            best_score = score
            best_thr = thr
    print(f"  >> Umbral recomendado por este corpus: {best_thr}")
    print(f"     (configurar RAG_SCORE_THRESHOLD={best_thr} en .env)")
    print()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def main() -> None:
    _sep("=")
    print("  LOREMASTER -- THRESHOLD EVALUATION")
    print("  Evalúa rag_score_threshold en: 0.0 / 0.3 / 0.5 / 0.7")
    print(f"  Modelo de embeddings : {EMBEDDING_MODEL}")
    print(f"  Chunk size / overlap : {CHUNK_SIZE} / {CHUNK_OVERLAP}")
    print(f"  top_k por consulta   : {TOP_K}")
    _sep("=")

    print("\n  Cargando modelo de embeddings...", end=" ", flush=True)
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("listo.")

    print("  Indexando corpus...", end=" ", flush=True)
    chunks, chunk_embeddings = build_index(SAMPLE_TEXT, model)
    print(f"listo. ({len(chunks)} chunks)")

    print(f"  Ejecutando {len(QUERIES)} consultas × {len(THRESHOLDS)} umbrales...\n")

    rows = run_evaluation(QUERIES, chunks, chunk_embeddings, model)

    # --- Detalle por consulta ---
    _sep("=")
    print("  DETALLE POR CONSULTA")
    for query in QUERIES:
        query_rows = [r for r in rows if r["query_id"] == query["id"]]
        _print_query_block(query, query_rows)

    # --- Resumen por umbral ---
    _print_threshold_summary(rows)

    # --- Recomendación ---
    _print_recommendation(rows)


if __name__ == "__main__":
    main()
