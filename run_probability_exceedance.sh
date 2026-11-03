#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 <pattern> --output-prefix PREFIX --gdal-output-dir DIR [probability_exceedance.py options]

Run probability_exceedance.py in a temporary GRASS mapset inside Docker.
All arguments other than -l/--location are passed to probability_exceedance.py.

Optional:
  -l, --location LOCATION (default: data/CDPG)

Example:
  $0 "data/ensemble/member_*.tif" \\
    --thresholds 50 100 --output-prefix prob \\
    --gdal-output-dir data/probability_exceedance/geotiff
EOF
}

location="data/CDPG"
script_args=()
gdal_output_dir=""
png_output_dir=""

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
        -h|--help)
            usage
            exit 0
            ;;
        --gdal_output_dir|--gdal-output-dir)
            if (($# < 2)) || [[ "$2" == -* ]]; then
                echo "Error: $1 requires a directory." >&2
                usage >&2
                exit 2
            fi
            gdal_output_dir="$2"
            shift 2
            ;;
        --png_output_dir|--png-output-dir)
            if (($# < 2)) || [[ "$2" == -* ]]; then
                echo "Error: $1 requires a directory." >&2
                usage >&2
                exit 2
            fi
            png_output_dir="$2"
            shift 2
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

if ((${#script_args[@]} == 0)); then
    echo "Error: provide the input pattern and probability_exceedance.py options." >&2
    usage >&2
    exit 2
fi

input_file_glob=${script_args[0]}
wdir=$(dirname "$input_file_glob")
input_file_glob="/work/$(basename "$input_file_glob")"
script_args[0]="$input_file_glob"

if [[ -z "${gdal_output_dir:-}" ]]; then
    echo "Error: --gdal-output-dir is required." >&2
    usage >&2
    exit 2
fi
gdal_output_dir="/work/$(basename "$gdal_output_dir")"

if [[ -n "${png_output_dir:-}" ]]; then
    png_output_dir="/work/$(basename "$png_output_dir")"
fi

service="app"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mapset="session_$(date +%s)"

docker compose \
    --project-directory "$script_dir" \
    run --rm -T \
    -v "$script_dir/public:/public:ro" \
    -v "$wdir:/work" \
    -e LOCATION="$location" \
    -e MAPSET="$mapset" \
    -e GDAL_OUTPUT_DIR="$gdal_output_dir" \
    -e PNG_OUTPUT_DIR="$png_output_dir" \
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
echo "--- Running probability_exceedance.py"
args=(--gdal-output-dir "$GDAL_OUTPUT_DIR")
if [[ -n "$PNG_OUTPUT_DIR" ]]; then
    args+=(--png-output-dir "$PNG_OUTPUT_DIR")
fi
grass "$LOCATION/$MAPSET" --exec /opt/venv/bin/python probability_exceedance.py "$@" "${args[@]}"
EOF
