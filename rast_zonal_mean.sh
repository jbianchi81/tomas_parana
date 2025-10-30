zones_file=tmp/areas_pluvio.tif
cover_file=tmp/pr.nc
output_dir=tmp/medias_zonales
coef=86400
method=average
# define region
g.region n=-10 s=-40 e=-40 w=-70 res=0.05
# carga capa de zonas
r.in.gdal $zones_file output=areas_pluvio --overwrite -o
# convierte a int
r.mapcalc "areas = int(areas_pluvio)" --overwrite
r.null map=areas setnull=0
# carga capa de cobertura
r.in.gdal $cover_file  output=cover --overwrite
# itera
for map in $(g.list type=raster pattern="cover.*" separator=newline); do
    echo "Processing $map ..."
    map_index=$(echo $map | cut -d. -f2)
    # reescala
    r.mapcalc "cover = $coef*$map" --overwrite
    # calcula medias zonales
    r.stats.zonal base=areas cover=cover method=$method output=media_zonal --overwrite
    # exporta a csv
    r.stats -n -A -c input=areas,media_zonal separator=comma > $output_dir/media_zonal.$map_index.csv
done