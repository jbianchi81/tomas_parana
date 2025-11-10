import pandas
import os
import re
from a5client import client
from datetime import datetime, timedelta
import json

from pytz import timezone

###### PARAMS ##########
input_dir = "data/series_q_arg_md"
output_dir = "data/series_q_arg_md_json"
client.url = "http://10.10.9.14:5008"
########################

files = os.listdir(input_dir)

for file in files:
    id_externo = re.match(r"\d+",file)[0]
    print("id_externo: %s" % id_externo)
    series_qmd_obs = client.readSeries(id_externo=id_externo, tabla="alturas_bdhi", var_id=40, proc_id=1)
    if "rows" not in series_qmd_obs or not len(series_qmd_obs["rows"]):
        print("No se encontró la serie de caudal medio diario de la estación con id externo = %s" % id_externo)
        continue
    serie = series_qmd_obs["rows"][0]
    print("Se encontró la serie id = %i" % serie["id"])
    # lee csv
    data = pandas.read_csv(open("%s/%s" % (input_dir,file)), sep=r"\s+", names = ["day", "month", "year", "valor"], na_values={"valor":"-1.000000"})
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
    json.dump(data[["timestart","valor","series_id","tipo"]].to_dict(orient="records"), open("%s/%i.json" % (output_dir, serie["id"]),"w", encoding="utf-8"), indent=2)






