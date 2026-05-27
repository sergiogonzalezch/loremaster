# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Instala dependencias y pre-descarga el embedding model.
# Resultado: /opt/venv con todo instalado y /root/.cache con el modelo.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-descargar el embedding model en tiempo de build para evitar cold-start.
# El modelo cachea en /root/.cache/huggingface/hub/ (~90 MB).
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Imagen final: solo lo necesario para ejecutar la app.
FROM python:3.12-slim

# Parchear paquetes del SO antes de cualquier otra capa.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Usuario no-root para reducir superficie de ataque.
RUN useradd -m -u 1000 loremaster

WORKDIR /app

# Copiar venv del builder (deps ya instaladas, sin pip ni build tools).
COPY --from=builder /opt/venv /opt/venv

# Copiar el cache del embedding model al home del usuario runtime.
COPY --from=builder /root/.cache /home/loremaster/.cache

ENV PATH="/opt/venv/bin:$PATH"

# Copiar código fuente.
COPY . .

# Crear directorio de media para que el volumen Docker herede los permisos correctos.
RUN mkdir -p /app/media

# Ajustar permisos: el usuario loremaster necesita el cache y el directorio de trabajo.
RUN chown -R loremaster:loremaster /home/loremaster/.cache /app

USER loremaster

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]