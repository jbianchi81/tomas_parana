## Configurar pydrodelta
Ingresar url y token del servidor de datos (a5 API)
```bash
nano $HOME/.a5client.ini
```
## Ejecutar plan en pydrodelta
```bash
planes_dir=$PWD"/data/plans"
# ir al directorio de pydrodelta
cd pydrodelta
# crear ambiente de python (saltear este paso si ya se creó)
python3 -m venv .venv
# activar ambiente de python
source .venv/bin/activate
# ejecutar plan
pydrodelta run-plan $planes_dir/mi_plan.yml
# ver resultados. Normalmente se guardan en data/results (ver archivo yml del plan)
ls -lrt data/results
```
En el archivo yml del plan se pueden configurar los archivos de resultados, como por ejemplo

descripción | ruta
--- | ---
Salida del procedimiento de análisis (condiciones de borde, json) | mi_plan.yml -> output_analysis
Reporte del procedimiento de análisis | mi_plan.yml -> topology -> report_file
Salida del procedimiento de análisis (condiciones de borde, csv) | mi_plan.yml -> topology -> output_csv
plots de las variables observadas y simuladas (pdf) | mi_plan.yml -> topology -> plot_variable -> [i] -> output
tablas de las variables observadas y simuladas (csv, json) | mi_plan.yml -> topology -> save_variable -> [i] -> output
tablas de salida de los procedimientos (csv) |mi_plan.yml -> procedures -> [i] -> save_results
resultados de la calibración: set de parámetros (json) | mi_plan.yml -> procedures -> [i] -> calibration -> save_result 
estadísticos de eficiencia cal/val (json) | mi_plan.yml -> output_stats
Salida del plan (series simuladas, json) | mi_plan.yml -> output_results
Salida del plan (series simuladas, csv) | mi_plan.yml -> output_sim_csv
Copia local del envío de resultados al servidor para almacenamiento en base de datos (json) |mi_plan.yml -> save_post
Respuesta del servidor | mi_plan.yml -> save_response
Variables simuladas en archivos separados (csv) | mi_plan.yml -> save_variable_sim -> [i] -> output
Grafo del plan (png) | mi_plan.yml -> output_graph

Las rutas relativas se resuelven con respecto al directorio base de pydrodelta. Para guardas archivos fuera del mismo, usar rutas absolutas.

Para editar el archivo de plan se recomienda usar una IDE con soporte para YAML, por ejemplo Visual Studio Code con la extensión 'YAML'
## log
/var/log/pydrodelta.log

## Probabilidades de excedencia en GRASS GIS

Con un mapset de GRASS activo, `probability_exceedance.py` importa cada raster
de una banda que coincida con el patron y crea un mapa porcentual por umbral.
El porcentaje se calcula sobre los miembros no nulos en cada celda. La
excedencia es estricta (`valor > umbral`). Cada mapa porcentual se exporta como
GeoTIFF. Antes de aplicar `r.colors`, se crea un raster temporal de cinco
categorias con cortes predeterminados en 5, 35, 65 y 95 por ciento. Las reglas
de color predeterminadas estan en
`data/probability_exceedance/default_color_rule`.

```bash
grass <GISDBASE>/<LOCATION>/<MAPSET> --exec \
  python /probability_exceedance.py "data/ensemble/member_*.tif" \
  --thresholds 50 100 \
  --output-prefix prob \
  --gdal-output-dir data/probability_exceedance/geotiff \
  --png-output-dir data/probability_exceedance/png
```

Los mapas GRASS y GeoTIFF se llaman `prob_exceed_50` y `prob_exceed_100`.
La exportacion PNG es opcional; omita `--png-output-dir` para desactivarla.
Use `--category-cuts CUT1 CUT2 CUT3 CUT4` para cambiar los cuatro cortes, o
`--color-rules PATH` para aplicar otro archivo `r.colors` con cinco colores
de categoria. Agregar `--overwrite` permite reemplazar mapas y archivos de
salida existentes.
