import json
from a5client import client
import pandas

filename = "data/estaciones_props.geojson"

estaciones = json.load(open(filename,encoding='utf-8'))

estaciones_a5 = client.readEstaciones(tabla='red_ana_hidro')
len(estaciones_a5)
estaciones_a5_id_externos = [ e["id_externo"] for e in estaciones_a5]

estaciones_nuevas = [e for e in estaciones["features"] if e["properties"]["id_externo"] not in estaciones_a5_id_externos ]

estaciones_nuevas_a5 = [ {
    **e["properties"],
    "geom": e["geometry"]
} for e in estaciones_nuevas]

creadas = client.createSites(estaciones_nuevas_a5, "estaciones","json")

len(creadas)
[e["id"] for e in creadas]

estaciones_a5_ = client.readEstaciones(tabla='red_ana_hidro')
len(estaciones_a5_)

series_q_obs = [{
    "estacion_id": e["id"],
    "var_id": 40,
    "proc_id": 1,
    "unit_id": 10
} for e in creadas]

series_q_sim = [{
    "estacion_id": e["id"],
    "var_id": 40,
    "proc_id": 4,
    "unit_id": 10
} for e in creadas]

series_creadas_1 = client.createSeries(series_q_obs)
len(series_creadas_1)

series_creadas_2 = client.createSeries(series_q_sim)
len(series_creadas_2)

# 2csv

est = []
for e in estaciones["features"]:
    id_externo = e["properties"]["id_externo"]
    for es in estaciones_a5_:
        if id_externo == es["id_externo"]:
            print("found estacion %s" % es["nombre"])
            est.append({
                "fid": e["properties"]["fid"],
                "id": e["properties"]["id_externo"],
                "x": e["geometry"]["coordinates"][0],
                "y": e["geometry"]["coordinates"][1],
                "nombre": es["nombre"],
                "estacion_id": es["id"]
            })


df = pandas.DataFrame(est)

df.to_csv("data/estaciones_2.csv")

# series to csv

series_puntuales = [*series_creadas_1, *series_creadas_2]

df_series_puntuales = pandas.DataFrame([{
     "id": s["id"],
     "estacion_id": s["estacion"]["id"],
     "var_id": s["var"]["id"],
     "proc_id": s["procedimiento"]["id"],
     "unit_id": s["unidades"]["id"],
     "variable": s["var"]["nombre"]
} for s in series_puntuales])

df_series_puntuales.to_csv("data/series_puntuales.csv",index=False)