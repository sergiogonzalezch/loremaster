# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Instala dependencias y pre-descarga el embedding model.
# Resultado: /opt/venv con todo instalado y /root/.cache con el modelo.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# Instalar torch CPU-only ANTES que el resto de requirements.
# Por defecto PyPI resuelve torch con CUDA (nvidia-cublas, cuda-toolkit, triton…)
# lo que añade ~4 GB innecesarios. Al pre-instalar la variante CPU, sentence-transformers
# lo encuentra ya satisfecho y no arrastra las CUDA libs.
RUN pip install --no-cache-dir torch \
        --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

# Pre-descargar el embedding model en tiempo de build para evitar cold-start.
# El modelo cachea en /root/.cache/huggingface/hub/ (~90 MB).
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Imagen final: solo lo necesario para ejecutar la app.
FROM python:3.12-slim

LABEL project=loremaster

# Parchear paquetes del SO antes de cualquier otra capa.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Usuario no-root para reducir superficie de ataque.
RUN useradd -m -u 1000 loremaster

WORKDIR /app

# Copiar venv del builder (deps ya instaladas, sin pip ni build tools).
COPY --from=builder /opt/venv /opt/venv

# Copiar el cache del embedding model directamente con ownership correcto,
# evitando un RUN chown posterior que duplicaría ~535 MB en una capa extra.
COPY --chown=loremaster:loremaster --from=builder /root/.cache /home/loremaster/.cache

ENV PATH="/opt/venv/bin:$PATH"

# Copiar código fuente con ownership correcto.
COPY --chown=loremaster:loremaster . .

# Crear media dir y fijar ownership del directorio /app (WORKDIR lo crea como root).
# Solo se chownean inodos vacíos — sin duplicación de datos.
RUN mkdir -p /app/media && chown loremaster:loremaster /app /app/media

USER loremaster

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]