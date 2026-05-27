BACKEND_DIR  = backend
FRONTEND_DIR = frontend
DC_BASE      = docker compose -f $(BACKEND_DIR)/docker-compose.yml
DC_PG        = $(DC_BASE) -f $(BACKEND_DIR)/docker-compose.postgres.yml
DC_PROD      = docker compose -f $(BACKEND_DIR)/docker-compose.prod.yml

.PHONY: dev dev-pg infra infra-pg down prod-up prod-down prod-rebuild prod-rebuild-api prod-rebuild-fe make-admin

# ── Entorno completo (SQLite) ────────────────────────────────────────────────
dev: infra
	powershell -ExecutionPolicy Bypass -File dev.ps1

# ── Entorno completo (PostgreSQL) ────────────────────────────────────────────
dev-pg: infra-pg
	powershell -ExecutionPolicy Bypass -File dev.ps1 -Postgres

# ── Solo infraestructura (SQLite) ────────────────────────────────────────────
infra:
	$(DC_BASE) up -d

# ── Solo infraestructura (PostgreSQL) ────────────────────────────────────────
infra-pg:
	$(DC_PG) up -d

# ── Bajar infraestructura local ───────────────────────────────────────────────
down:
	$(DC_PG) down

# ── Producción / Demo ─────────────────────────────────────────────────────────
prod-up:
	$(DC_PROD) up -d

prod-down:
	$(DC_PROD) down

# Reconstruye todos los servicios con build: (app + frontend).
prod-rebuild:
	$(DC_PROD) up -d --build

# Rebuild selectivo: solo el backend Python.
prod-rebuild-api:
	$(DC_PROD) up -d --build app

# Rebuild selectivo: solo el frontend (cambios React/CSS).
prod-rebuild-fe:
	$(DC_PROD) up -d --build frontend

# Promueve un usuario a admin en el stack de demo/producción.
# Requiere que loremaster-api esté corriendo (make prod-up).
# Uso: make make-admin USER=serchglez
make-admin:
	$(if $(USER),,$(error Uso: make make-admin USER=^<username^>))
	docker exec -it loremaster-api python scripts/make_admin.py $(USER) --force
