from a5client import client
import json

# crear areas

areas_geojson_file = "data/restantes_geo.geojson"

areas_geojson = json.load(open(areas_geojson_file))
len(areas_geojson["features"])

estaciones_a5 = client.readEstaciones(tabla='alturas_bdhi') # red_ana_hidro

areas_ = []
for a in areas_geojson["features"]:
    found=False
    id_externo = str(a["properties"]["nombre"])
    for e in estaciones_a5:
        if e["id_externo"] == id_externo:
            print("se encontró estación %s" % e["nombre"])
            found=True
            areas_.append({
                "nombre": e["nombre"],
                "geom": a["geometry"],
                "exutorio": e["geom"],
                "exutorio_id": e["id"],
                "activar": True,
                "mostrar": False
            })
            continue
    if not found:
        print("no se encontró id_externo=%s" % id_externo)

len(areas_)

areas = client.createSites(areas_, "areas", "json")

# sin exutorio
areas_ = [{
    "nombre": a["properties"]["nombre"],
    "geom": a["geometry"],
    "activar": True,
    "mostrar": False
} for a in areas_geojson["features"]]

areas = client.createSites(areas_, "areas", "json")

#

area_ids = [area["id"] for area in areas]  # area_ids = [905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023, 1024, 1025, 1026, 1027, 1028, 1029, 1030, 1031, 1032, 1033, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1044, 1045, 1046, 1047]

# crear series areales

# CPC, campo, GFS, GPM, ETP, PERSIANN

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
    { "tipo": "areal", "area_id": None, "proc_id": 4, "var_id": 1,"unit_id": 22, "fuentes_id": 5},
    { "tipo": "areal", "area_id": None, "proc_id": 6, "var_id": 1,"unit_id": 22, "fuentes_id": 51}
]

created_series = []
for area_id in area_ids:
    series = [ {**t, "area_id": area_id} for t in templates ]
    created_series.extend(client.createSeries(series, tipo="areal"))

len(created_series)

# area_ids = range(797,863)
areas_arg = ",".join([str(a) for a in area_ids])


# poblar series areales

bash_commands = open("tmp/generar_areales.sh","w")
# CPC

bash_commands.write(" && ".join(["bash pp_areal_to_db.sh -f 2 -s 19900101 -e 20000101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 2 -s 20000101 -e 20100101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 2 -s 20100101 -e 20200101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 2 -s 20200101 -e 20251021 -U -a %s\n" % areas_arg]))

# campo

bash_commands.write(" && ".join(["bash pp_areal_to_db.sh -f 7 -s 19900101 -e 20000101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 7 -s 20000101 -e 20100101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 7 -s 20100101 -e 20200101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 7 -s 20200101 -e 20251021 -U -a %s\n" % areas_arg]))


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

json.dump(asociaciones, open("data/asociaciones_gpm_5.json", "w"), ensure_ascii=False)

bash_commands.write("a5cli create asociacion data/asociaciones_gpm_5.json -o data/asociaciones_gpm_4_creadas.json\n")

# corre asociaciones

bash_commands.write("node crud_procedures.js run-asoc 2020-01-01 2025-10-07 source_tipo=raster source_series_id=13 %s" % " ".join([ "dest_estacion_id=%i" % id for id in area_ids]))

# WM (ETP)

bash_commands.write(" && ".join(["bash pp_areal_to_db.sh -f 3 -s 19900101 -e 20000101 -U -a %s" % areas_arg, 
"bash pp_areal_to_db.sh -f 3 -s 20000101 -e 20100101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 3 -s 20100101 -e 20200101 -U -a %s" % areas_arg,
"bash pp_areal_to_db.sh -f 3 -s 20200101 -e 20300101 -U -a %s\n" % areas_arg]))

bash_commands.close()

series_areal_todas= []
for area_id in [778,779,780,781,782,783,784]:
    series_areal_todas.extend(client.readSeries("areal",estacion_id=area_id)["rows"])

len(series_areal_todas)

import pandas

df = pandas.DataFrame([{ "id": s["id"], "area_id": s["estacion"]["id"], "proc_id": s["procedimiento"]["id"], "var_id":s["var"]["id"],"unit_id":s["unidades"]["id"], "fuentes_id": s["fuente"]["id"], "nombre": s["fuente"]["nombre"]} for s in created_series]) # series_areal_todas])

df.to_csv("data/series_areales4.csv",index=False)

# areas to csv

# areas = []
# for id in [778,779,780,781,782,783,784]:
#     areas.append(client.readArea(id))

# df = pandas.DataFrame([
#     {
#         "id": a["id"],
#         "nombre": a["nombre"],
#         "area": a["area"],
#         "exutorio_id": a["exutorio_id"]
#     } for a in areas
# ])
# df.to_csv("data/areas_3.csv")

# areas 2 geojson

features = [{
        "type": "Feature",
        "properties": { "nombre": a["nombre"], "id": a["id"]}, 
        "geometry": a["geom"]
    } for a in areas]

agj = open("data/areas_faltantes_con_id.geojson","w")
json.dump({
    "type": "FeatureCollection",
    "name": "areas_faltantes_con_id",
    "crs": {
        "type": "name",
        "properties": {
            "name": "EPSG:4326"
        }
    },
    "features": features
},agj, indent=2, ensure_ascii=False)
agj.close()

### series areales modelos

fuentes_ids = range(53,73)

area_ids = [905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023, 1024, 1025, 1026, 1027, 1028, 1029, 1030, 1031, 1032, 1033, 1034, 1035, 1036, 1037, 1038, 1039, 1040, 1041, 1042, 1043, 1044, 1045, 1046, 1047]


series_areales_pr_modelos = [
    {
        "tipo": "areal",
        "fuentes_id": fuentes_id,
        "area_id": area_id,
        "var_id": 1,
        "unit_id": 22,
        "proc_id": 4
    } for area_id in area_ids for fuentes_id in fuentes_ids
]

client.createSeries(series_areales_pr_modelos, tipo="areal")

series_areales_etp_modelos = [
    {
        "tipo": "areal",
        "fuentes_id": fuentes_id,
        "area_id": area_id,
        "var_id": 15,
        "unit_id": 22,
        "proc_id": 4
    } for area_id in area_ids for fuentes_id in fuentes_ids
]

client.createSeries(series_areales_etp_modelos, tipo="areal")


