# dev.ps1 — Levanta el entorno de desarrollo completo de LoreMaster.
#
# Uso:
#   .\dev.ps1            → infraestructura SQLite + backend + frontend
#   .\dev.ps1 -Postgres  → infraestructura PostgreSQL + backend + frontend
#
# Prerequisitos:
#   - Docker Desktop corriendo
#   - Python en PATH
#   - Node instalado (npm)

param(
    [switch]$Postgres
)

$Root = $PSScriptRoot

# ── 0. Venv del backend ──────────────────────────────────────────────────────
$VenvDir = "$Root\backend\venv"
$Pip     = "$VenvDir\Scripts\pip"

if (-not (Test-Path $VenvDir)) {
    Write-Host "==> Creando entorno virtual..." -ForegroundColor Yellow
    python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] No se pudo crear el venv. Verifica que Python esté en PATH." -ForegroundColor Red
        exit 1
    }
}

Write-Host "==> Verificando dependencias del backend..." -ForegroundColor Cyan
& $Pip install -q -r "$Root\backend\requirements.txt" -r "$Root\backend\requirements-dev.txt"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip install falló. Revisa requirements.txt / requirements-dev.txt." -ForegroundColor Red
    exit 1
}

# ── 1. Infraestructura Docker ────────────────────────────────────────────────
Write-Host ""
Write-Host "==> Levantando infraestructura..." -ForegroundColor Cyan

if ($Postgres) {
    docker compose -f "$Root\backend\docker-compose.yml" -f "$Root\backend\docker-compose.postgres.yml" up -d
} else {
    docker compose -f "$Root\backend\docker-compose.yml" up -d
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] docker compose falló. Verifica que Docker Desktop esté corriendo." -ForegroundColor Red
    exit 1
}

# ── 2. Backend ───────────────────────────────────────────────────────────────
Write-Host "==> Abriendo backend (http://localhost:8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\backend'; .\venv\Scripts\Activate.ps1; make run"
)

# ── 3. Frontend ──────────────────────────────────────────────────────────────
Write-Host "==> Abriendo frontend (http://localhost:5173)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\frontend'; npm run dev"
)

# ── Resumen ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Entorno listo:" -ForegroundColor Green
Write-Host "  Backend  → http://localhost:8000       (docs: /docs)" -ForegroundColor Green
Write-Host "  Frontend → http://localhost:5173" -ForegroundColor Green
Write-Host "  Qdrant   → http://localhost:6333" -ForegroundColor Green
if ($Postgres) {
    Write-Host "  Postgres → localhost:5433" -ForegroundColor Green
} else {
    Write-Host "  DB       → SQLite (backend/loremaster.db)" -ForegroundColor Green
}
Write-Host ""
Write-Host "Para bajar: make down" -ForegroundColor DarkGray
