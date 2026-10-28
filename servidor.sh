#!/usr/bin/env bash
#
# servidor.sh - Levanta o detiene el entorno de desarrollo de Mixer:
#   db (PostgreSQL en Docker), backend (FastAPI) y frontend (Angular).
#
# Uso:
#   ./servidor.sh --on      Arranca db, aplica migraciones + seed y lanza API y web en screen
#   ./servidor.sh --off     Detiene web, API y db
#   ./servidor.sh --status  Muestra el estado de cada servicio
#

set -u

# --- Configuración --------------------------------------------------------
SESION_BACK="mixer-backend"
SESION_FRONT="mixer-frontend"
PUERTO_BACK=8000
PUERTO_FRONT=4200
START_TIMEOUT=180 # segundos máximos esperando a que un servicio acepte conexiones
STOP_TIMEOUT=30   # segundos máximos esperando a que un servicio se cierre

# Directorio donde está este script (raíz del repo)
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

# uv vive en ~/.local/bin y Node 22 en nvm; no siempre están en el PATH
export PATH="$HOME/.local/bin:$PATH"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
# shellcheck disable=SC1091
[[ -s "$NVM_DIR/nvm.sh" ]] && { set +u; . "$NVM_DIR/nvm.sh"; nvm use 22 >/dev/null; set -u; }

# --- Colores ANSI (se desactivan si la salida no es una terminal) ---------
if [[ -t 1 ]]; then
    VERDE=$'\e[1;32m'; ROJO=$'\e[1;31m'; AMARILLO=$'\e[1;33m'
    AZUL=$'\e[1;34m'; NEGRITA=$'\e[1m'; RESET=$'\e[0m'
else
    VERDE=""; ROJO=""; AMARILLO=""; AZUL=""; NEGRITA=""; RESET=""
fi

ok()    { echo -e "${VERDE}[ OK ]${RESET} $*"; }
error() { echo -e "${ROJO}[ERROR]${RESET} $*" >&2; }
aviso() { echo -e "${AMARILLO}[AVISO]${RESET} $*"; }
info()  { echo -e "${AZUL}[INFO]${RESET} $*"; }

uso() {
    echo -e "${NEGRITA}Uso:${RESET} $(basename "$0") ${AMARILLO}--on${RESET} | ${AMARILLO}--off${RESET} | ${AMARILLO}--status${RESET}"
    echo
    echo "  --on      Levanta db, backend (:${PUERTO_BACK}) y frontend (:${PUERTO_FRONT})"
    echo "  --off     Detiene frontend, backend y db"
    echo "  --status  Indica qué servicios están encendidos"
}

# Devuelve 0 si existe una sesión de screen con el nombre exacto $1
sesion_activa() {
    screen -ls 2>/dev/null | grep -qE "^[[:space:]]+[0-9]+\.$1[[:space:]]"
}

# Devuelve 0 si algo acepta conexiones en el puerto $1
puerto_abierto() {
    timeout 2 bash -c "echo > /dev/tcp/127.0.0.1/$1" 2>/dev/null
}

db_activa() {
    [[ -n "$(docker compose -f "$SCRIPT_DIR/docker-compose.yml" ps -q --status running db 2>/dev/null)" ]]
}

# --- Servicios --------------------------------------------------------------
# lanzar <sesión> <puerto> <directorio> <comando>
# Ejecuta el comando en una sesión de screen separada, con log en logs/<sesión>.log,
# y espera a que el puerto acepte conexiones.
lanzar() {
    local sesion=$1 puerto=$2 dir=$3 cmd=$4 log="$LOG_DIR/$1.log"

    if sesion_activa "$sesion"; then
        aviso "'${sesion}' ya está ENCENDIDO (screen -r ${sesion})."
        return 0
    fi

    info "Iniciando '${sesion}'..."
    : > "$log"
    screen -dmS "$sesion" -L -Logfile "$log" bash -c "cd '$dir' && $cmd"

    local t=0
    while (( t < START_TIMEOUT )); do
        if ! sesion_activa "$sesion"; then
            echo
            error "'${sesion}' se ha cerrado durante el arranque. Revisa ${log}"
            return 1
        fi
        puerto_abierto "$puerto" && break
        sleep 1
        (( t++ ))
        printf '\r%s[....]%s Esperando a %s... %ds' "$AMARILLO" "$RESET" "$sesion" "$t"
    done
    echo

    if puerto_abierto "$puerto"; then
        ok "'${sesion}' ${VERDE}ENCENDIDO${RESET} en http://localhost:${puerto} (consola: screen -r ${sesion}; log: ${log})"
    else
        error "'${sesion}' no responde en el puerto ${puerto} tras ${START_TIMEOUT}s. Revisa ${log}"
        return 1
    fi
}

# detener <sesión>: Ctrl+C a la consola y, si no cierra a tiempo, mata la sesión.
detener() {
    local sesion=$1
    if ! sesion_activa "$sesion"; then
        aviso "'${sesion}' ya estaba APAGADO."
        return 0
    fi

    info "Deteniendo '${sesion}'..."
    screen -S "$sesion" -p 0 -X stuff $'\003'
    local t=0
    while sesion_activa "$sesion" && (( t < STOP_TIMEOUT )); do
        sleep 1
        (( t++ ))
    done
    sesion_activa "$sesion" && screen -S "$sesion" -X quit
    ok "'${sesion}' ${ROJO}APAGADO${RESET}."
}

# --- Acciones ---------------------------------------------------------------
encender() {
    mkdir -p "$LOG_DIR"

    info "Levantando la base de datos..."
    docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d --wait db \
        || { error "No se pudo levantar la base de datos."; return 1; }
    ok "db ${VERDE}ENCENDIDA${RESET} en localhost:5432"

    # El seed es idempotente: se puede ejecutar en cada arranque.
    lanzar "$SESION_BACK" "$PUERTO_BACK" "$SCRIPT_DIR/backend" \
        "uv run alembic upgrade head && uv run python -m scripts.seed && uv run fastapi dev --port $PUERTO_BACK" \
        || return 1

    lanzar "$SESION_FRONT" "$PUERTO_FRONT" "$SCRIPT_DIR/frontend" \
        "{ [ -d node_modules ] || npm install; } && NG_CLI_ANALYTICS=false npm start -- --port $PUERTO_FRONT"
}

apagar() {
    detener "$SESION_FRONT"
    detener "$SESION_BACK"
    if db_activa; then
        info "Deteniendo la base de datos..."
        docker compose -f "$SCRIPT_DIR/docker-compose.yml" stop db >/dev/null 2>&1 \
            && ok "db ${ROJO}APAGADA${RESET}." \
            || { error "No se pudo detener la base de datos."; return 1; }
    else
        aviso "db ya estaba APAGADA."
    fi
}

estado() {
    if db_activa; then ok "db ${VERDE}ENCENDIDA${RESET}"; else echo -e "${ROJO}[ OFF ]${RESET} db"; fi
    local s p
    for s in "$SESION_BACK:$PUERTO_BACK" "$SESION_FRONT:$PUERTO_FRONT"; do
        p=${s#*:}; s=${s%%:*}
        if ! sesion_activa "$s"; then
            echo -e "${ROJO}[ OFF ]${RESET} ${s}"
        elif puerto_abierto "$p"; then
            ok "${s} ${VERDE}ENCENDIDO${RESET} en http://localhost:${p}"
        else
            aviso "${s}: sesión activa, pero el puerto ${p} aún no responde (cargando o colgado)."
        fi
    done
}

# --- Comprobaciones previas -------------------------------------------------
for dep in screen docker uv npm; do
    command -v "$dep" >/dev/null 2>&1 || { error "'${dep}' no está instalado o no está en el PATH."; exit 1; }
done

# --- Punto de entrada -------------------------------------------------------
case "${1:-}" in
    --on)     encender ;;
    --off)    apagar ;;
    --status) estado ;;
    *)
        [[ -n "${1:-}" ]] && error "Argumento no válido: '$1'"
        uso
        exit 2
        ;;
esac
