import pandas
import os
import re
from a5client import client
from datetime import datetime, timedelta
import json

from pytz import timezone

files = os.listdir("data/series_q")

for file in files:
    id_externo = re.match(r"\d{4}",file)[0]
    print("id_externo: %s" % id_externo)
    series_qmd_obs = client.readSeries(id_externo=id_externo, tabla="alturas_bdhi", var_id=40, proc_id=1)
    if "rows" not in series_qmd_obs or not len(series_qmd_obs["rows"]):
        print("No se encontró la serie de caudal medio diario de la estación con id externo = %s" % id_externo)
        continue
    serie = series_qmd_obs["rows"][0]
    print("Se encontró la serie id = %i" % serie["id"])
    # lee csv
    data = pandas.read_csv(open("data/series_q/%s" % file), sep=r"\s+", names = ["day", "month", "year", "valor"], na_values={"valor":"-1.000000"})
    # borra nulos
    data.dropna(inplace=True)
    # concatena fecha
    data["timestart"] = pandas.to_datetime(data[["year","month","day"]])
    data["timestart"] = data["timestart"].dt.tz_localize("America/Argentina/Buenos_Aires", nonexistent="shift_forward")
    data["series_id"] = serie["id"]
    data["tipo"] = "puntual"
    data["timestart"] = data["timestart"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    created = client.createObservaciones(data[["timestart","valor","series_id","tipo"]].to_dict(orient="records"), serie["id"], timeSupport = timedelta(days=1))
    # created = client.createObservaciones(data[["timestart","valor","series_id","tipo"]], serie["id"], timeSupport = timedelta(days=1))
    created
    json.dump(data[["timestart","valor","series_id","tipo"]].to_dict(orient="records"), open("data/series_q_json/%i.json" % serie["id"],"w", encoding="utf-8"), indent=2)






