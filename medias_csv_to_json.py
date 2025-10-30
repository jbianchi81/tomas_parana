import os
import datetime
import pandas
import json
from a5client import client
import argparse

def getSeries(fuentes_id : int):
    series_areales = pandas.DataFrame(client.readSeries("areal",fuentes_id=fuentes_id, no_metadata=True)["rows"])
    series_areales.set_index("estacion_id", inplace=True)
    return series_areales

def parseCSVFile(
        filepath : str, year : int, 
        series_areales : pandas.DataFrame, 
        dt : datetime.timedelta,
        offset_hours : int = 0):
    print("parseando %s" % filepath)
    doy = int(filepath.split(".")[1])
    date = datetime.datetime(year,1,1) + datetime.timedelta(days=doy - 1, hours=offset_hours)
    data = pandas.read_csv(filepath)
    data.columns=["estacion_id","valor","cell_count"]
    data.set_index("estacion_id", inplace=True)
    joined = data.join(series_areales)
    joined["timestart"] = date
    joined["timeend"] = date + dt
    return joined[["series_id", "valor", "timestart", "timeend"]]

def readDir(
        dirname : str, year : int, 
        fuentes_id : int,
        dt: datetime.timedelta,
        output : str = None,
        offset_hours : int = 0):
    series_areales : pandas.DataFrame = getSeries(fuentes_id)
    obs = [] # pandas.DataFrame(columns={"series_id": int, "valor": float, "timestart": datetime, "timeend": datetime})
    files = os.listdir(dirname)
    for file in files:
        filepath = "%s/%s" % (dirname, file)
        obs.append(parseCSVFile(filepath, year, series_areales, dt, offset_hours))
    allobs = pandas.concat(obs, ignore_index=True)
    if output is not None:
        allobs.to_json(output,orient="records", date_format='iso', indent=2)
    return allobs

#### params #####
# params = {
#     "dirname": "tmp/medias_zonales",
#     "year": 2014,
#     "fuentes_id": 53,
#     "dt": datetime.timedelta(days=1)
# }
#################
# python medias_csv_to_json.py -y 2014 -f 53 tmp/medias_zonales medias_zonales_f53_2014.json

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dirname", type=str)
    parser.add_argument("output", type=str)
    parser.add_argument("-y","--year", type=int, required=True)
    parser.add_argument("-f","--fuentes_id", type=int, required=True)
    parser.add_argument("-d","--dt", type=datetime.timedelta, default=datetime.timedelta(days=1))
    parser.add_argument("-o","--offset_hours", type=int, default=0)
    args = parser.parse_args()
    readDir(args.dirname, args.year, args.fuentes_id, args.dt, args.output, args.offset_hours)
