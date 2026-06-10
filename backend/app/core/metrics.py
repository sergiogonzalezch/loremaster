"""Singleton metric objects para Prometheus.

Todos los contadores e histogramas se definen aquí para evitar registros
duplicados si el módulo se importa desde varios archivos simultáneamente.
"""

from prometheus_client import Counter, Histogram

# ── RAG pipeline ──────────────────────────────────────────────────────────────

rag_queries_total = Counter(
    "loremaster_rag_queries_total",
    "Total de queries RAG ejecutadas",
    ["status"],  # success | error
)

cache_hits_total = Counter(
    "loremaster_cache_hits_total",
    "Queries RAG servidas desde caché semántica",
)

cache_misses_total = Counter(
    "loremaster_cache_misses_total",
    "Queries RAG que no encontraron hit en caché",
)

llm_requests_total = Counter(
    "loremaster_llm_requests_total",
    "Invocaciones al LLM (Ollama)",
    ["status"],  # success | error
)

llm_duration_seconds = Histogram(
    "loremaster_llm_duration_seconds",
    "Duración de la generación LLM en segundos",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

# ── Document ingestion ────────────────────────────────────────────────────────

document_ingestions_total = Counter(
    "loremaster_document_ingestions_total",
    "Documentos ingestados",
    ["status"],  # success | error
)

# ── Image generation ──────────────────────────────────────────────────────────

image_generations_total = Counter(
    "loremaster_image_generations_total",
    "Generaciones de imagen ejecutadas",
    ["backend", "status"],  # backend: comfyui|runpod|mock, status: success|error
)

# ── Moderation ────────────────────────────────────────────────────────────────

moderation_blocks_total = Counter(
    "loremaster_moderation_blocks_total",
    "Contenido bloqueado por el sistema de moderación",
    ["layer"],  # input | output
)
