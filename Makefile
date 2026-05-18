BACKEND_DIR  = backend
FRONTEND_DIR = frontend
DC_BASE      = docker compose -f $(BACKEND_DIR)/docker-compose.yml
DC_PG        = $(DC_BASE) -f $(BACKEND_DIR)/docker-compose.postgres.yml
DC_PROD      = docker compose -f $(BACKEND_DIR)/docker-compose.prod.yml

.PHONY: dev dev-pg infra infra-pg down prod-up prod-down

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
	$(DC_BASE) down
	-docker stop postgres
	-docker rm   postgres

# ── Producción / Demo ─────────────────────────────────────────────────────────
prod-up:
	$(DC_PROD) up -d

prod-down:
	$(DC_PROD) down
