#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------------------
# Run GRASS GIS + Python zonal_means.py inside a Docker container
# Creates a temporary mapset, runs per-year processing, cleans up
# --------------------------------------------------------------------
# Usage:
#   ./run_zonal_means.sh <template> <start> <end> <output> <fuentes_id> <var_id> <coef> <zones_file>
#
# --------------------------------------------------------------------

if [ "$#" -ne 8 ]; then
  echo "Usage: $0 <template> <start> <end> <output> <fuentes_id> <var_id> <coef> <zones_file>"
  exit 1
fi

template="$1"
start="$2"
end="$3"
output="$4"
fuentes_id="$5"
var_id="$6"
coef="$7"
zones_file="$8"

service="app"
location="data/WGS84/cmip1"
# --------------------------------------------------------------------
# Execute everything inside the container
# --------------------------------------------------------------------

docker compose run --name tomas_parana-app-run-f$fuentes_id-v$var_id-s$start-e$end  --rm -T \
  -e LOCATION="$location" \
  -e TEMPLATE="$template" \
  -e START="$start" \
  -e END="$end" \
  -e OUTPUT="$output" \
  -e FUENTES_ID="$fuentes_id" \
  -e VAR_ID="$var_id" \
  -e COEF="$coef" \
  -e ZONES_FILE="$zones_file" \
  "$service" bash -s <<'EOF'
set -euo pipefail

mapset=session_$(date +%s)

echo "--- Creating mapset: $mapset"
grass "$LOCATION/PERMANENT" --exec g.mapset -c mapset="$mapset"
for year in $(seq $START $END); do
    echo "--- Processing year: $year"
    ncfile="${TEMPLATE//%Y/$year}"
    grass "$LOCATION/$mapset" --exec /opt/venv/bin/python zonal_means.py \
        "$ncfile" "$OUTPUT" -f "$FUENTES_ID" -v "$VAR_ID" -c "$COEF" -z $ZONES_FILE -u
done

echo "--- Deleting mapset: $mapset"
rm -rf "$LOCATION/$mapset"
EOF

echo "✅ Finished zonal means for ${start}-${end}"
