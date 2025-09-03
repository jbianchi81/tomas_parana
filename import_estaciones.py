import json
from a5client import client
import pandas

filename = "data/estaciones/estaciones_props.geojson"

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


estaciones_nuevas = [e for e in estaciones_a5 if e["id_externo"] in list(map(lambda f: f["properties"]["id_externo"],estaciones["features"])) ]

len(estaciones_nuevas)
estaciones_nuevas[0]

series_q_inst = [{
    "estacion_id": e["id"],
    "var_id": 4,
    "proc_id": 1,
    "unit_id": 10
} for e in estaciones_nuevas]

creadas_inst = client.createSeries(series_q_inst)

asoc_hmd = []
for serie_source in creadas_inst:
    series_dest = client.readSeries(tipo="puntual", var_id=40, proc_id=1, unit_id=10, estacion_id=serie_source["estacion"]["id"])
    if not len(series_dest["rows"]):
        print("No se encontro serie dest para estacion id %i" % serie_source["estacion"]["id"])
        continue
    serie_dest = series_dest["rows"][0]
    asoc_hmd.append({
        "source_tipo": "puntual",
        "source_series_id": serie_source["id"],
        "dest_tipo": "puntual",
        "dest_series_id": serie_dest["id"],
        "agg_func": "avg",
        "dt": "1 day",
        "t_offset": "00:00:00",
        "precision": 2,
        "habilitar": True
    })

json.dump(asoc_hmd, open("data/asoc_hmd.json","w"), indent=2)