# ── Stage 1: build ────────────────────────────────────────────────────────────
# Compila el bundle de producción con Vite.
FROM node:22-alpine AS builder

WORKDIR /app

# Instalar dependencias primero (capa cacheada si package.json no cambia).
COPY package*.json ./
RUN npm ci

# Copiar fuentes y compilar.
COPY . .

# VITE_API_BASE_URL relativo: el build funciona en cualquier host sin cambios.
# Nginx proxea /api/ → backend, /media/ → Floci, todo mismo origen.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

RUN npm run build


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Nginx sirve el bundle estático y actúa como reverse proxy.
FROM nginx:alpine

# Reemplazar config por defecto con la nuestra (proxy rules incluidas).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar bundle compilado.
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]