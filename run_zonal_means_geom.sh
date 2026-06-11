#!/usr/bin/env bash
set -euo pipefail

# Defaults
cover_file=""
output=""
zones_file="data/zones.tif"
geom_file="" # "data/zones.geojson"
dates_file="data/dates.csv"
cor_id=""
fuentes_id=""
var_id=""
coef=1.0
dt="PT1D"
round_to=2
upload=false
series_file=""

usage() {
    echo "Usage: $0 -c <cover_file> -o <output> -g <vector_zones_file> -z <raster_zones_file> -t <dates_file> -o <cor_id> -f <fuentes_id> -v <var_id> [options]"
    echo
    echo "Required:"
    echo "  -c COVER_FILE"
    echo "  -o OUTPUT"
    echo "  -f FUENTES_ID"
    echo "  -v VAR_ID"
    echo "  -t DATES_FILE"
    echo "  -i COR_ID"
    echo
    echo "Optional:"
    echo "  -k COEF         (default: $coef)"
    echo "  -d DT           (default: '$dt')"
    echo "  -r ROUND_TO     (default: $round_to)"
    echo "  -z RASTER_ZONES_FILE (default: $zones_file)"
    echo "  -g VECTOR_ZONES_FILE"
    echo "  -u"
    echo "  -s SERIES_FILE"
    exit 1
}

while getopts ":c:o:f:v:k:z:g:d:r:t:i:uhs:" opt; do
    case "$opt" in
        c) cover_file="$OPTARG" ;;
        o) output="$OPTARG" ;;
        f) fuentes_id="$OPTARG" ;;
        v) var_id="$OPTARG" ;;
        k) coef="$OPTARG" ;;
        z) zones_file="$OPTARG" ;;
        g) geom_file="$OPTARG" ;;
        d) dt="$OPTARG" ;;
        r) round_to="$OPTARG" ;;
        t) dates_file="$OPTARG" ;;
        i) cor_id="$OPTARG" ;;
        u) upload=true ;;
        s) series_file="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Check required args
: "${cover_file:?Missing -c COVER_FILE}"
: "${output:?Missing -o OUTPUT}"
: "${fuentes_id:?Missing -f FUENTES_ID}"
: "${var_id:?Missing -v VAR_ID}"
: "${dates_file:?Missing -d DATES_FILE}"
# : "${cor_id:?Missing -c COR_ID}"

service="app"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
location="data/ZONALMEANS"
wdir=$(dirname "$output")
cover_file="/work/$(basename "$cover_file")"
output="/work/$(basename "$output")"
dates_file="/work/$(basename "$dates_file")"
[ -n "$zones_file" ] && zones_file="/work/$(basename "$zones_file")"
[ -n "$geom_file" ] && geom_file="/work/$(basename "$geom_file")"
[ -n "$series_file" ] && series_file="/work/$(basename "$series_file")"

# --------------------------------------------------------------------
# Execute everything inside the container
# --------------------------------------------------------------------
ts=$(date +"%M.%S.%s")

docker compose \
  --project-directory "$SCRIPT_DIR" \
  run --name tomas_parana-app-run-f$fuentes_id-v$var_id-t$ts --rm -T \
  -v "$wdir:/work" \
  -e LOCATION="$location" \
  -e COVER_FILE="$cover_file" \
  -e OUTPUT="$output" \
  -e FUENTES_ID="$fuentes_id" \
  -e VAR_ID="$var_id" \
  -e COEF="$coef" \
  -e ZONES_FILE="$zones_file" \
  -e DT="$dt" \
  -e ROUND_TO="$round_to" \
  -e DATES_FILE="$dates_file" \
  -e COR_ID="$cor_id" \
  -e GEOM_FILE="$geom_file" \
  -e UPLOAD="$upload" \
  -e SERIES_FILE="$series_file" \
  "$service" bash -s <<'EOF'
set -euo pipefail

args=()
if [ -n "$GEOM_FILE" ]; then
    args+=(-g $GEOM_FILE -Z)
fi

if [ "${UPLOAD:-false}" = "true" ]; then
    args+=(-u)
fi

if [ -n "$SERIES_FILE" ]; then
    args+=(-s $SERIES_FILE)
fi

if [ -n "$COR_ID" ]; then
    args+=(-C $COR_ID)
fi


mapset=session_$(date +%s)

echo "--- Creating mapset: $mapset"
grass "$LOCATION/PERMANENT" --exec g.mapset -c mapset="$mapset"
echo "--- Processing file: $COVER_FILE"
# echo "grass $LOCATION/$mapset --exec /opt/venv/bin/python zonal_means.py $COVER_FILE $OUTPUT -f $FUENTES_ID -v $VAR_ID -c $COEF -z $ZONES_FILE -d $DT -r $ROUND_TO -a $DATES_FILE -C $COR_ID ${args[@]}"
grass "$LOCATION/$mapset" --exec /opt/venv/bin/python zonal_means.py \
    "$COVER_FILE" "$OUTPUT" -f "$FUENTES_ID" -v "$VAR_ID" -c "$COEF" -z "$ZONES_FILE" -d "$DT" -r "$ROUND_TO" -a "$DATES_FILE" "${args[@]}"

echo "--- Deleting mapset: $mapset"
rm -rf "$LOCATION/$mapset"
EOF

echo "✅ Finished zonal means for ${cover_file}"


# python zonal_means.py -f 50 -v 91 -D data/gfs_csv -z data/areas_pluvio.tif -d PT6H -c 1 -a data/index.csv data/gfs_nomads.tif data/gfs_areal.json -r 2
# ./run_zonal_means_geom.sh -c data/gfs_nomads.tif -g data/gfs_areal.json -f 50 -v 91 -k 1 -z /tmp/areas_pluvio.tif -d PT6H -t data/index.csv 