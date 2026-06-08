#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------------------
# Run GRASS GIS + Python zonal_means.py inside a Docker container
# Creates a temporary mapset, runs per-year processing, cleans up
# --------------------------------------------------------------------
# Usage:
#   ./run_zonal_means_one.sh <cover_file> <output> <fuentes_id> <var_id> <coef> <zones_file> <dt> <round_to> <dates_file> 
#
# --------------------------------------------------------------------

if [ "$#" -ne 9 ]; then
  echo "Usage: $0 <cover_file> <output> <fuentes_id> <var_id> <coef> <zones_file> <dt> <round_to> <dates_file> "
  exit 1
fi

cover_file="$1"
output="$2"
fuentes_id="$3"
var_id="$4"
coef="$5"
zones_file="$6"
dt="$7"
round_to="$8"
dates_file="$9"

service="app"
location="data/ZONALMEANS"
# --------------------------------------------------------------------
# Execute everything inside the container
# --------------------------------------------------------------------
ts=$(date +"%M.%S.%s")

docker compose run --name tomas_parana-app-run-f$fuentes_id-v$var_id-t$ts --rm -T \
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
  "$service" bash -s <<'EOF'
set -euo pipefail

mapset=session_$(date +%s)

echo "--- Creating mapset: $mapset"
grass "$LOCATION/PERMANENT" --exec g.mapset -c mapset="$mapset"
echo "--- Processing file: $COVER_FILE"
grass "$LOCATION/$mapset" --exec /opt/venv/bin/python zonal_means.py \
    "$COVER_FILE" "$OUTPUT" -f "$FUENTES_ID" -v "$VAR_ID" -c "$COEF" -z "$ZONES_FILE" -d "$DT" -r "$ROUND_TO" -a "$DATES_FILE"

echo "--- Deleting mapset: $mapset"
rm -rf "$LOCATION/$mapset"
EOF

echo "✅ Finished zonal means for ${cover_file}"


# python zonal_means.py -f 50 -v 91 -D data/gfs_csv -z data/areas_pluvio.tif -d PT6H -c 1 -a data/index.csv data/gfs_nomads.tif data/gfs_areal.json -r 2
# ./run_zonal_means_one.sh data/gfs_nomads.tif data/gfs_areal.json 50 91 1 data/areas_pluvio.tif PT6H 2 data/index.csv 