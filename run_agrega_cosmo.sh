#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 [agrega_cosmo.py options] [--location LOCATION]

Run agrega_cosmo.py in a temporary GRASS mapset inside Docker.
All script options are passed to agrega_cosmo.py.

GRASS option:
  -l, --location LOCATION (default: data/CDPG)

agrega_cosmo.py options:
  --emision YYYYMMDD
  --inicializacion HH
  --null NODATA
  --cut-diario STEPS
  --host DIR
  --host-3h DIR
  --host-1d DIR
EOF
}

location="data/CDPG"
host="data/cosmo"
host_3h="data/cosmo/3_horario"
host_1d="data/cosmo/diario"
script_args=()

while (($#)); do
    case "$1" in
        -l|--location)
            if (($# < 2)) || [[ "$2" == -* ]]; then
                echo "Error: $1 requires a LOCATION." >&2
                usage >&2
                exit 2
            fi
            location="$2"
            shift 2
            ;;
        --location=*)
            location="${1#*=}"
            shift
            ;;
        --host|--host-3h|--host-1d)
            if (($# < 2)) || [[ "$2" == -* ]]; then
                echo "Error: $1 requires a directory." >&2
                usage >&2
                exit 2
            fi
            case "$1" in
                --host) host="$2" ;;
                --host-3h) host_3h="$2" ;;
                --host-1d) host_1d="$2" ;;
            esac
            shift 2
            ;;
        --host=*|--host-3h=*|--host-1d=*)
            value="${1#*=}"
            case "${1%%=*}" in
                --host) host="$value" ;;
                --host-3h) host_3h="$value" ;;
                --host-1d) host_1d="$value" ;;
            esac
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            script_args+=("$@")
            break
            ;;
        *)
            script_args+=("$1")
            shift
            ;;
    esac
done

if [[ ! -d "$host" ]]; then
    echo "Error: input directory not found: $host" >&2
    exit 2
fi

host="$(cd -- "$host" && pwd)"
mkdir -p -- "$host_3h" "$host_1d"
host_3h="$(cd -- "$host_3h" && pwd)"
host_1d="$(cd -- "$host_1d" && pwd)"

service="app"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mapset="session_$(date +%s)"

echo "host=$host"
echo "host_3h=$host_3h"
echo "host_1d=$host_1d"
echo "script_dir=$script_dir"

docker compose \
    --project-directory "$script_dir" \
    run --rm -T \
    -v "$host:/cosmo-input:ro" \
    -v "$host_3h:/cosmo-output-3h" \
    -v "$host_1d:/cosmo-output-1d" \
    -e LOCATION="$location" \
    -e MAPSET="$mapset" \
    "$service" bash -s -- "${script_args[@]}" <<'EOF'
set -euo pipefail

cleanup() {
    if [[ -d "$LOCATION/$MAPSET" ]]; then
        echo "--- Deleting mapset: $MAPSET"
        rm -rf -- "$LOCATION/$MAPSET"
    fi
}
trap cleanup EXIT

echo "--- Creating mapset: $MAPSET"
grass "$LOCATION/PERMANENT" --exec g.mapset -c "mapset=$MAPSET"
echo "--- Running agrega_cosmo.py"
grass "$LOCATION/$MAPSET" --exec /opt/venv/bin/python agrega_cosmo.py \
    "$@" \
    --host /cosmo-input \
    --host-3h /cosmo-output-3h \
    --host-1d /cosmo-output-1d
EOF
