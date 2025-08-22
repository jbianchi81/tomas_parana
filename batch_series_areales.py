from a5client import client
import json

# crear areas

areas_geojson_file = "/home/alerta7/Downloads/cuencas_tomas_parana/cuencas_tomas_parana.geojson"

areas_geojson = json.load(open(areas_geojson_file))

areas = client.createSites(areas_geojson, "areas", "geojson")

#

area_ids = [area["id"] for area in areas]  # area_ids = [740, 741, 742, 743]

# crear series areales

# CPC, campo, GFS, GPM, ETP

templates = [
    { "tipo": "areal", "area_id": None, "proc_id": 3, "var_id": 1,"unit_id": 22, "fuentes_id": 7},
    { "tipo": "areal", "area_id": None, "proc_id": 4, "var_id": 1,"unit_id": 22, "fuentes_id": 50},
    { "tipo": "areal", "area_id": None, "proc_id": 4, "var_id": 1,"unit_id": 22, "fuentes_id": 39},
    { "tipo": "areal", "area_id": None, "proc_id": 5, "var_id": 1,"unit_id": 22, "fuentes_id": 6},
    { "tipo": "areal", "area_id": None, "proc_id": 5, "var_id": 1,"unit_id": 22, "fuentes_id": 11},
    { "tipo": "areal", "area_id": None, "proc_id": 6, "var_id": 1,"unit_id": 22, "fuentes_id": 2},
    { "tipo": "areal", "area_id": None, "proc_id": 7, "var_id": 15,"unit_id": 22, "fuentes_id": 3},
    { "tipo": "areal", "area_id": None, "proc_id": 5, "var_id": 20,"unit_id": 23, "fuentes_id": 15},
    { "tipo": "areal", "area_id": None, "proc_id": 4, "var_id": 91,"unit_id": 9, "fuentes_id": 50},
    { "tipo": "areal", "area_id": None, "proc_id": 4, "var_id": 1,"unit_id": 22, "fuentes_id": 5}
]

created_series = []
for area_id in area_ids:
    series = [ {**t, "area_id": area_id} for t in templates ]
    created_series.extend(client.createSeries(series, tipo="areal"))


areas_arg = ",".join([str(a) for a in area_ids])

# poblar series areales

# CPC

" && ".join(["bash pp_areal_to_db.sh -f 2 -s 19900101 -e 20000101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 2 -s 20000101 -e 20100101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 2 -s 20100101 -e 20200101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 2 -s 20200101 -e 20250823 -U -a %s" % areas_arg])

# campo

" && ".join(["bash pp_areal_to_db.sh -f 7 -s 19900101 -e 20000101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 7 -s 20000101 -e 20100101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 7 -s 20100101 -e 20200101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 7 -s 20200101 -e 20250823 -U -a %s" % areas_arg])


# GFS

# GPM

# crea asociaciones rast 2 areal

template_asoc_gpm = {
    "source_tipo": "raster",
    "source_series_id": 13,
    "dest_tipo": "areal",
    "dest_series_id": None,
    "dt": "1 day",
    "t_offset": "12:00:00",
    "precision": 2,
    "habilitar": True
}

series_areal_gpm = []
for area_id in area_ids:
    series_areal_gpm.extend(client.readSeries("areal",fuentes_id=6,estacion_id=area_id)["rows"])

asociaciones = [{**template_asoc_gpm, "dest_series_id": s["id"]} for s in series_areal_gpm]

json.dump(asociaciones, open("data/asociaciones_gpm.json", "w"), ensure_ascii=False)

"a5cli create asociacion data/asociaciones_gpm.json -o data/asociaciones_gpm_creadas.json --pretty" 

# corre asociaciones

"node crud_procedures.js run-asoc 2020-01-01 2025-08-23 source_tipo=raster source_series_id=13 %s" % " ".join([ "dest_estacion_id=%i" % id for id in area_ids])

# WM (ETP)

" && ".join(["bash pp_areal_to_db.sh -f 3 -s 19900101 -e 20000101 -U -a %s" % areas_arg, 
"bash pp_areal_to_db.sh -f 3 -s 20000101 -e 20100101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 3 -s 20100101 -e 20200101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 3 -s 20200101 -e 20300101 -U -a %s" % areas_arg])