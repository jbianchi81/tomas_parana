#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 [match.py options] [--location LOCATION]

Run match.py in a temporary GRASS mapset inside Docker.
All script options are passed to match.py.

GRASS option:
  -l, --location LOCATION (default: data/CDPG)

match.py options:
  [input_1] [input_2]
  --resolution DEGREES
  --window-size CELLS
  --fuzzy-threshold FRACTION
  --thresholds VALUE [VALUE ...]
  --title TITLE
  --output PATH
  --workdir PATH (must contain the inputs and output)
EOF
}

location="data/CDPG"
input_1="data/match/input_1.tif"
input_2="data/match/input_2.tif"
output="data/match/DangerMap.tif"
workdir=""
script_args=()
input_count=0

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
        -w|--workdir)
            if (($# < 2)) || [[ "$2" == -* ]]; then
                echo "Error: $1 requires a workdir." >&2
                usage >&2
                exit 2
            fi
            workdir="$2"
            shift 2
            ;;
        --workdir=*)
            workdir="${1#*=}"
            shift
            ;;
        --output)
            if (($# < 2)); then
                echo "Error: --output requires a path." >&2
                usage >&2
                exit 2
            fi
            output="$2"
            shift 2
            ;;
        --output=*)
            output="${1#*=}"
            shift
            ;;
        --resolution|--window-size|--fuzzy-threshold|--title)
            if (($# < 2)); then
                echo "Error: $1 requires a value." >&2
                usage >&2
                exit 2
            fi
            script_args+=("$1" "$2")
            shift 2
            ;;
        --thresholds)
            script_args+=("$1")
            shift
            while (($#)) && [[ "$1" != -* ]]; do
                script_args+=("$1")
                shift
            done
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
        -*)
            script_args+=("$1")
            shift
            ;;
        *)
            if ((input_count == 0)); then
                input_1="$1"
            elif ((input_count == 1)); then
                input_2="$1"
            else
                script_args+=("$1")
            fi
            ((input_count += 1))
            shift
            ;;
    esac
done

workdir="${workdir:-$(dirname -- "$input_1")}"
if [[ ! -d "$workdir" ]]; then
    echo "Error: work directory not found: $workdir" >&2
    exit 2
fi
workdir="$(realpath -- "$workdir")"
input_1="$(realpath -e -- "$input_1")"
input_2="$(realpath -e -- "$input_2")"
output="$(realpath -m -- "$output")"

container_path() {
    local path="$1"
    if [[ "$path" == "$workdir/"* ]]; then
        printf '/match-workdir/%s' "${path#"$workdir"/}"
    else
        echo "Error: $path must be inside work directory $workdir." >&2
        return 2
    fi
}

input_1_container="$(container_path "$input_1")"
input_2_container="$(container_path "$input_2")"
output_container="$(container_path "$output")"

service="app"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mapset="session_$(date +%s)"

docker compose \
    --project-directory "$script_dir" \
    run --rm -T \
    -v "$workdir:/match-workdir" \
    -v "$script_dir/public:/public:ro" \
    -e LOCATION="$location" \
    -e MAPSET="$mapset" \
    "$service" bash -s -- \
    "$input_1_container" "$input_2_container" \
    --output "$output_container" "${script_args[@]}" <<'EOF'
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
echo "--- Running match.py"
grass "$LOCATION/$MAPSET" --exec /opt/venv/bin/python match.py "$@"
EOF
