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

ensure_venv() {
    local backend_dir="$(pwd)/backend"
    if [ ! -d "$backend_dir/venv" ]; then
        echo -e "${Y}  Creando entorno virtual...${Z}"
        python3 -m venv "$backend_dir/venv"
    fi
    echo -e "${C}  Verificando dependencias del backend...${Z}"
    "$backend_dir/venv/bin/pip" install -q \
        -r "$backend_dir/requirements.txt" \
        -r "$backend_dir/requirements-dev.txt"
}

open_terminal() {
    local title="$1"
    local cmd="$2"
    local dir="$3"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        osascript -e "tell application \"Terminal\" to do script \"cd '$dir' && $cmd\""
    elif command -v gnome-terminal &>/dev/null; then
        gnome-terminal --title="$title" -- bash -c "cd '$dir'; $cmd; exec bash"
    elif command -v xterm &>/dev/null; then
        xterm -title "$title" -e "bash -c \"cd '$dir'; $cmd; exec bash\"" &
    else
        echo -e "${D}  Sin terminal GUI: ejecuta manualmente: cd '$dir' && $cmd${Z}"
    fi
}

stop_services() {
    echo
    echo -e "${C}  Cerrando servicios...${Z}"
    local b_pid f_pid
    b_pid=$(lsof -ti:8000 2>/dev/null || true)
    f_pid=$(lsof -ti:5173 2>/dev/null || true)
    if [ -n "$b_pid" ]; then
        kill "$b_pid" 2>/dev/null && echo -e "${D}  Backend  (8000) cerrado.${Z}" || true
    fi
    if [ -n "$f_pid" ]; then
        kill "$f_pid" 2>/dev/null && echo -e "${D}  Frontend (5173) cerrado.${Z}" || true
    fi
    make down 2>/dev/null && echo -e "${D}  Infra Docker bajada.${Z}" || true
    echo -e "${G}  Todo cerrado.${Z}"
    echo
}

dev_up() {
    local postgres="$1"
    echo
    ensure_venv
    echo
    if [ "$postgres" = "true" ]; then
        echo -e "${C}  Levantando infra PostgreSQL...${Z}"
        docker compose -f backend/docker-compose.yml -f backend/docker-compose.postgres.yml up -d
    else
        echo -e "${C}  Levantando infra SQLite (Qdrant + Redis)...${Z}"
        docker compose -f backend/docker-compose.yml up -d
    fi
    echo -e "${C}  Abriendo backend...${Z}"
    open_terminal "loremaster-backend" "source venv/bin/activate && make run" "$(pwd)/backend"
    echo -e "${C}  Abriendo frontend...${Z}"
    open_terminal "loremaster-frontend" "npm run dev" "$(pwd)/frontend"
    echo
    echo -e "${G}  Entorno listo:${Z}"
    echo -e "    Backend  -> http://localhost:8000"
    echo -e "    Frontend -> http://localhost:5173"
    echo -e "    Qdrant   -> http://localhost:6333"
}

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
            sleep 2; menu ;;
        2)
            dev_up true
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
