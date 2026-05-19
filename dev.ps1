# dev.ps1 — Levanta el entorno de desarrollo completo de LoreMaster.
#
# Uso:
#   .\dev.ps1            -> infraestructura SQLite + backend + frontend
#   .\dev.ps1 -Postgres  -> infraestructura PostgreSQL + backend + frontend
#
# Prerequisitos:
#   - Docker Desktop corriendo
#   - Python en PATH
#   - Node/npm en PATH
#   - Ollama corriendo (para funciones LLM)

param(
    [switch]$Postgres
)

$Root = $PSScriptRoot

# ── 0. Prerequisitos ─────────────────────────────────────────────────────────
$prereqOk = $true

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python no encontrado en PATH. Instala Python 3.9+." -ForegroundColor Red
    $prereqOk = $false
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] npm no encontrado en PATH. Instala Node.js." -ForegroundColor Red
    $prereqOk = $false
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker no está corriendo. Inicia Docker Desktop." -ForegroundColor Red
    $prereqOk = $false
}

if (-not $prereqOk) { exit 1 }

$ollamaUp = (Test-NetConnection -ComputerName localhost -Port 11434 -WarningAction SilentlyContinue).TcpTestSucceeded
if (-not $ollamaUp) {
    Write-Host "[AVISO] Ollama no responde en localhost:11434. Inicialo antes de usar funciones LLM." -ForegroundColor Yellow
}

# ── 1. Venv del backend ──────────────────────────────────────────────────────
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
$backendProc = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\backend'; .\venv\Scripts\Activate.ps1; make run"
) -PassThru
$backendProc.Id | Out-File "$Root\.loremaster_backend_pid" -Encoding ascii

# ── 2.5. Esperar a que el backend esté listo ─────────────────────────────────
Write-Host "==> Esperando backend en :8000 " -ForegroundColor Yellow -NoNewline
$maxWait = 120; $elapsed = 0; $ready = $false
while ($elapsed -lt $maxWait -and -not $ready) {
    Start-Sleep -Seconds 2; $elapsed += 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true }
    } catch {}
    if (-not $ready) { Write-Host -NoNewline "." }
}
if ($ready) { Write-Host " Listo!" -ForegroundColor Green }
else { Write-Host " Timeout - arrancando frontend de todas formas." -ForegroundColor Yellow }

# ── 3. Frontend ──────────────────────────────────────────────────────────────
Write-Host "==> Abriendo frontend (http://localhost:5173)..." -ForegroundColor Cyan
$frontendProc = Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$Root\frontend'; npm run dev"
) -PassThru
$frontendProc.Id | Out-File "$Root\.loremaster_frontend_pid" -Encoding ascii

# ── Resumen ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Entorno listo:" -ForegroundColor Green
Write-Host "  Backend  -> http://localhost:8000       (docs: /docs)" -ForegroundColor Green
Write-Host "  Frontend -> http://localhost:5173" -ForegroundColor Green
Write-Host "  Qdrant   -> http://localhost:6333" -ForegroundColor Green
if ($Postgres) {
    Write-Host "  Postgres -> localhost:5433" -ForegroundColor Green
} else {
    Write-Host "  DB       -> SQLite (backend/loremaster.db)" -ForegroundColor Green
}
Write-Host ""
Write-Host "Para bajar: make down" -ForegroundColor DarkGray
