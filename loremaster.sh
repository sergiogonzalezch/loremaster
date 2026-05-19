#!/usr/bin/env bash
set -uo pipefail

cd "$(dirname "$0")"

C='\033[0;96m'
Y='\033[0;93m'
G='\033[0;92m'
R='\033[0;91m'
D='\033[0;90m'
W='\033[0;97m'
Z='\033[0m'

# true cuando se ejecuta desde Git Bash o Cygwin en Windows
_is_win() { [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; }

# ── Prerequisitos ─────────────────────────────────────────────────────────────
check_prereqs() {
    local ok=true

    if ! command -v python3 &>/dev/null; then
        echo -e "${R}  [ERROR] python3 no encontrado en PATH. Instala Python 3.9+.${Z}"
        ok=false
    fi
    if ! command -v npm &>/dev/null; then
        echo -e "${R}  [ERROR] npm no encontrado en PATH. Instala Node.js.${Z}"
        ok=false
    fi
    if ! docker info > /dev/null 2>&1; then
        echo -e "${R}  [ERROR] Docker no está corriendo. Inicia Docker Desktop / dockerd.${Z}"
        ok=false
    fi
    if [ "$ok" = "false" ]; then
        echo -e "${R}  Corrige los errores anteriores antes de continuar.${Z}"
        return 1
    fi
    if ! curl -sf --max-time 2 http://localhost:11434 > /dev/null 2>&1; then
        echo -e "${Y}  [AVISO] Ollama no responde en localhost:11434 — inícialo antes de usar funciones LLM.${Z}"
    fi
}

# ── Venv ──────────────────────────────────────────────────────────────────────
ensure_venv() {
    local backend_dir="$(pwd)/backend"
    if [ ! -d "$backend_dir/venv" ]; then
        echo -e "${Y}  Creando entorno virtual...${Z}"
        python3 -m venv "$backend_dir/venv"
    fi
    echo -e "${C}  Verificando dependencias del backend...${Z}"
    local pip_bin
    _is_win && pip_bin="$backend_dir/venv/Scripts/pip" \
            || pip_bin="$backend_dir/venv/bin/pip"
    "$pip_bin" install -q \
        -r "$backend_dir/requirements.txt" \
        -r "$backend_dir/requirements-dev.txt"
}

# ── Abrir terminal (guarda PID en $4 si se pasa) ──────────────────────────────
open_terminal() {
    local title="$1"
    local cmd="$2"
    local dir="$3"
    local pid_file="${4:-}"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        osascript -e "tell application \"Terminal\" to do script \"cd '$dir' && $cmd\""
    elif _is_win; then
        mintty -t "$title" bash -c "cd '$dir' && $cmd; exec bash" &
        [ -n "$pid_file" ] && echo $! > "$pid_file"
    elif command -v gnome-terminal &>/dev/null; then
        gnome-terminal --title="$title" -- bash -c "cd '$dir'; $cmd; exec bash" &
        [ -n "$pid_file" ] && echo $! > "$pid_file"
    elif command -v xterm &>/dev/null; then
        xterm -title "$title" -e "bash -c \"cd '$dir'; $cmd; exec bash\"" &
        [ -n "$pid_file" ] && echo $! > "$pid_file"
    else
        echo -e "${D}  Sin terminal GUI: ejecuta manualmente: cd '$dir' && $cmd${Z}"
    fi
}

# ── Parar servicios ───────────────────────────────────────────────────────────
stop_services() {
    echo
    echo -e "${C}  Cerrando servicios...${Z}"
    local w_pid r_pid

    # lsof -sTCP:LISTEN devuelve el worker (el que tiene el socket).
    # ps -o ppid= sube al reloader (padre), que no tiene socket y sobreviviría.
    w_pid=$(lsof -ti:8000 -sTCP:LISTEN 2>/dev/null | head -1 || true)
    if [ -n "$w_pid" ]; then
        r_pid=$(ps -o ppid= -p "$w_pid" 2>/dev/null | tr -d ' ' || true)
        kill "$w_pid" 2>/dev/null || true
        if [ -n "$r_pid" ] && [ "$r_pid" -gt 1 ] 2>/dev/null; then
            kill "$r_pid" 2>/dev/null || true
        fi
        echo -e "${D}  Backend  (8000) cerrado.${Z}"
    fi
    if [ -f ".loremaster_backend_pid" ]; then
        kill "$(cat .loremaster_backend_pid)" 2>/dev/null || true
        rm -f .loremaster_backend_pid
    fi

    w_pid=$(lsof -ti:5173 -sTCP:LISTEN 2>/dev/null | head -1 || true)
    if [ -n "$w_pid" ]; then
        r_pid=$(ps -o ppid= -p "$w_pid" 2>/dev/null | tr -d ' ' || true)
        kill "$w_pid" 2>/dev/null || true
        if [ -n "$r_pid" ] && [ "$r_pid" -gt 1 ] 2>/dev/null; then
            kill "$r_pid" 2>/dev/null || true
        fi
        echo -e "${D}  Frontend (5173) cerrado.${Z}"
    fi
    if [ -f ".loremaster_frontend_pid" ]; then
        kill "$(cat .loremaster_frontend_pid)" 2>/dev/null || true
        rm -f .loremaster_frontend_pid
    fi

    docker compose -f backend/docker-compose.yml down 2>/dev/null \
        && echo -e "${D}  Infra Docker bajada.${Z}" || true
    docker stop postgres 2>/dev/null; docker rm postgres 2>/dev/null; true
    echo -e "${G}  Todo cerrado.${Z}"
    echo
}

# ── Levantar entorno de desarrollo ────────────────────────────────────────────
dev_up() {
    local postgres="$1"
    echo
    check_prereqs || { read -r -p "  Pulsa Enter para volver al menú..."; return 1; }
    ensure_venv
    echo

    if [ "$postgres" = "true" ]; then
        echo -e "${C}  Levantando infra PostgreSQL...${Z}"
        docker compose -f backend/docker-compose.yml -f backend/docker-compose.postgres.yml up -d
    else
        echo -e "${C}  Levantando infra SQLite (Qdrant + Redis)...${Z}"
        docker compose -f backend/docker-compose.yml up -d
    fi

    local activate_cmd
    _is_win && activate_cmd="source venv/Scripts/activate" \
            || activate_cmd="source venv/bin/activate"

    # ── Backend ────────────────────────────────────────────────────────────────
    echo -e "${C}  Abriendo backend (http://localhost:8000)...${Z}"
    open_terminal "loremaster-backend" "$activate_cmd && make run" "$(pwd)/backend" ".loremaster_backend_pid"

    # ── Esperar health (max 120s) ──────────────────────────────────────────────
    printf "  Esperando backend en :8000 "
    local max_wait=120 elapsed=0 ready=false
    while [ "$elapsed" -lt "$max_wait" ] && [ "$ready" = "false" ]; do
        sleep 2; elapsed=$((elapsed + 2))
        if curl -sf --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
            ready=true
        else
            printf "."
        fi
    done
    if [ "$ready" = "true" ]; then
        echo -e " ${G}Listo!${Z}"
    else
        echo -e " ${Y}Timeout - arrancando frontend de todas formas.${Z}"
    fi

    # ── Frontend ───────────────────────────────────────────────────────────────
    echo -e "${C}  Abriendo frontend (http://localhost:5173)...${Z}"
    open_terminal "loremaster-frontend" "npm run dev" "$(pwd)/frontend" ".loremaster_frontend_pid"

    # ── Resumen ────────────────────────────────────────────────────────────────
    echo
    echo -e "${G}  Entorno listo:${Z}"
    echo -e "    Backend  -> http://localhost:8000       (docs: /docs)"
    echo -e "    Frontend -> http://localhost:5173"
    echo -e "    Qdrant   -> http://localhost:6333"
    if [ "$postgres" = "true" ]; then
        echo -e "    Postgres -> localhost:5433"
    else
        echo -e "    DB       -> SQLite (backend/loremaster.db)"
    fi
    echo
}

# ── Menú ──────────────────────────────────────────────────────────────────────
menu() {
    clear
    echo
    echo -e "  ${C}+==========================================+${Z}"
    echo -e "  ${C}+${Z}       ${W}LOREMASTER  --  DEV LAUNCHER${Z}        ${C}+${Z}"
    echo -e "  ${C}+==========================================+${Z}"
    echo
    echo -e "  ${Y}LOCAL${Z}"
    echo -e "   ${G} 1${Z}  Dev SQLite        ./loremaster.sh"
    echo -e "   ${G} 2${Z}  Dev PostgreSQL    ./loremaster.sh"
    echo
    echo -e "  ${Y}INFRA${Z}"
    echo -e "   ${G} 3${Z}  Levantar SQLite   make infra"
    echo -e "   ${G} 4${Z}  Levantar Postgres make infra-pg"
    echo -e "   ${G} 5${Z}  Bajar todo        make down"
    echo
    echo -e "  ${Y}TESTS${Z}"
    echo -e "   ${G} 6${Z}  Ejecutar suite    cd backend && make test"
    echo
    echo -e "  ${Y}PRODUCCION / DEMO${Z}"
    echo -e "   ${G} 7${Z}  Prod UP           make prod-up"
    echo -e "   ${G} 8${Z}  Prod DOWN         make prod-down"
    echo
    echo -e "   ${R} 9${Z}  Salir y cerrar servicios"
    echo
    printf "  > "
    read -r -n1 OPT
    echo

    case "$OPT" in
        1)
            dev_up false
            echo -e "${D}  Ventanas abiertas. Volviendo al menú...${Z}"
            sleep 2; menu ;;
        2)
            dev_up true
            echo -e "${D}  Ventanas abiertas. Volviendo al menú...${Z}"
            sleep 2; menu ;;
        3)
            echo; echo -e "${C}  Levantando infra SQLite...${Z}"; echo
            make infra
            echo; echo -e "${G}  Listo.${Z}"
            read -r -p "  Pulsa Enter para continuar..."
            menu ;;
        4)
            echo; echo -e "${C}  Levantando infra PostgreSQL...${Z}"; echo
            make infra-pg
            echo; echo -e "${G}  Listo.${Z}"
            read -r -p "  Pulsa Enter para continuar..."
            menu ;;
        5)
            echo; echo -e "${C}  Bajando infraestructura...${Z}"; echo
            make down
            echo; echo -e "${G}  Listo.${Z}"
            read -r -p "  Pulsa Enter para continuar..."
            menu ;;
        6)
            echo; echo -e "${C}  Ejecutando tests...${Z}"; echo
            pushd backend >/dev/null
            make test
            popd >/dev/null
            echo
            read -r -p "  Pulsa Enter para continuar..."
            menu ;;
        7)
            echo; echo -e "${C}  Levantando produccion / demo...${Z}"; echo
            make prod-up
            echo; echo -e "${G}  Listo.${Z}"
            read -r -p "  Pulsa Enter para continuar..."
            menu ;;
        8)
            echo; echo -e "${C}  Bajando produccion...${Z}"; echo
            make prod-down
            echo; echo -e "${G}  Listo.${Z}"
            read -r -p "  Pulsa Enter para continuar..."
            menu ;;
        9|q|Q)
            stop_services
            exit 0 ;;
        *)
            menu ;;
    esac
}

menu
