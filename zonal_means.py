import os
import datetime
import pandas
from a5client import client
import argparse
#!/usr/bin/env python3
import os
import tempfile
import shutil
import json
import subprocess
import re

defaults = {
    "dt": datetime.timedelta(days=1),
    "coef": 86400,
    "method": "average",
    "zones_file": "data/areas_pluvio.tif",
    "geom_file": "data/areas_pluvio.geojson",
    "offset_hours": 9,
    "file_pattern": r".+_(\d{4})(_v\d\.\d)?\.nc",
    "a5_url": "http://10.10.9.14:5008",
    "var_id": 1
}

client.url = defaults["a5_url"]

def createZonesMap(geom_output : str, zones_file : str, filter: dict={}):
    areas = client.readAreas(**filter, format="geojson")
    # sort by area desc
    areas["features"].sort(
        key=lambda feat: feat["properties"].get("area", 0),
        reverse=True
    )
    json.dump(areas, open(geom_output, "w"), indent=2, ensure_ascii=False)
    try:
        subprocess.run(["gdal_rasterize","-of","GTiff","-a","id","-a_srs","EPSG:4326","-te","-70","-40","-40","-10","-tr","0.05","0.05","-ot","Int16",geom_output, zones_file], check=True)
    except subprocess.CalledProcessError as e:
        raise e

def zonalMeans(zones_file : str, cover_file : str, csvdir : str, coef : int, method: str):
    import grass.script as gs

    os.environ["GRASS_VERBOSE"] = "-1"

    # Ensure output directory exists
    os.makedirs(csvdir, exist_ok=True)

    # --- Define region ---
    gs.run_command("g.region", n=-10, s=-40, e=-40, w=-70, res=0.05)

    # --- Load zones raster ---
    gs.run_command("r.in.gdal", input=zones_file, output="areas_pluvio", overwrite=True, flags="o")

    # Convert to int and mask out 0
    gs.run_command("r.mapcalc", expression="areas = int( areas_pluvio )", overwrite=True)
    gs.run_command("r.null", map="areas", setnull=0)

    # --- Load cover raster (multiband) ---
    gs.run_command("r.in.gdal", input=cover_file, output="cover", overwrite=True, flags="o")

    # --- Iterate over each band ---
    cover_maps = gs.list_grouped("raster", pattern="cover.*")[gs.gisenv()["MAPSET"]]

    for cover_map in sorted(cover_maps):
        print(f"Processing {cover_map} ...")
        map_index = cover_map.split(".")[-1]  # e.g. 'cover.12' → '12'

        # Rescale
        gs.run_command("r.mapcalc", expression=f"cover_scaled = {coef} * {cover_map}", overwrite=True)

        # Zonal statistics (mean)
        gs.run_command(
            "r.stats.zonal",
            base="areas",
            cover="cover_scaled",
            method=method,
            output="media_zonal",
            overwrite=True
        )

        # Export results to CSV
        csv_path = os.path.join(csvdir, f"media_zonal.{map_index}.csv")
        with open(csv_path, "w") as f:
            gs.run_command(
                "r.stats",
                flags="nAc",  # -n -A -c
                input="areas,media_zonal",
                separator="comma",
                stdout=f
            )

        print(f" → saved {csv_path}")

    print("✅ Done.")

def getSeries(fuentes_id : int, var_id: int):
    series_areales = pandas.DataFrame(client.readSeries("areal",fuentes_id=fuentes_id, var_id=var_id, no_metadata=True)["rows"])
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
        var_id : int,
        dt: datetime.timedelta,
        output : str = None,
        offset_hours : int = 0,
        upload : bool = False):
    series_areales : pandas.DataFrame = getSeries(fuentes_id, var_id)
    obs = [] # pandas.DataFrame(columns={"series_id": int, "valor": float, "timestart": datetime, "timeend": datetime})
    files = os.listdir(dirname)
    for file in files:
        filepath = "%s/%s" % (dirname, file)
        obs.append(parseCSVFile(filepath, year, series_areales, dt, offset_hours))
    allobs = pandas.concat(obs, ignore_index=True)
    allobs.dropna(inplace=True)
    if output is not None:
        allobs.to_json(output,orient="records", date_format='iso', indent=2)
    if upload:
        # for series_id, group in allobs.groupby("series_id"):
        #     observaciones = group.set_index("timestart")
        #     print("Uploading series_id: %i" % series_id)
        #     client.createObservaciones(observaciones, series_id, tipo="areal")
        i=0
        while i < len(allobs):
            y = i + 10000
            print("Uploading observaciones %i to %i " % (i, min(y,len(allobs))))
            created = client.createObservaciones(allobs[i:y], tipo="areal")
            print("Created %i observaciones" % len(created))
            i = y
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


def run(args : argparse.Namespace):
    if args.csvdir is None:
        args.__setattr__("csvdir",tempfile.mkdtemp(prefix="zonal_means_tmp_"))
        print(f"🧩 Using temporary directory: {args.csvdir}")
        is_tmpdir = True
    else:
        is_tmpdir = False
    try:
        if not args.skip_grass_process:
            zonalMeans(args.zones_file, args.cover_file, args.csvdir, args.coef, args.method)
        readDir(args.csvdir, args.year, args.fuentes_id, args.var_id, args.dt, args.output, args.offset_hours, args.upload)
    finally:
        if is_tmpdir:
            # --- Clean up temporary directory ---
            print(f"🧹 Cleaning up temporary directory: {args.csvdir}")
            shutil.rmtree(args.csvdir, ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cover_file", type=str)
    parser.add_argument("output", type=str)
    parser.add_argument("-y","--year", type=int)
    parser.add_argument("-f","--fuentes_id", type=int, required=True)
    parser.add_argument("-v","--var_id", type=int, default=defaults["var_id"])
    parser.add_argument("-D","--csvdir", type=str)
    parser.add_argument("-z","--zones_file", type=str, default=defaults["zones_file"])
    parser.add_argument("-d","--dt", type=datetime.timedelta, default=defaults["dt"])
    parser.add_argument("-o","--offset_hours", type=int, default=defaults["offset_hours"])
    parser.add_argument("-c","--coef", type=float, default=defaults["coef"])
    parser.add_argument("-m","--method", type=str, default=defaults["method"])
    parser.add_argument("-u","--upload",action="store_true")
    parser.add_argument("-S","--skip_grass_process",action="store_true")
    parser.add_argument("-Z","--create_zones_map",action="store_true")
    parser.add_argument("--geom_file", type=str, default=defaults["geom_file"])
    parser.add_argument("-p","--file_pattern", type=str, default=defaults["file_pattern"])
    parser.add_argument("-U","--a5_url", type=str, default=defaults["a5_url"])
    args = parser.parse_args()
    client.url = args.a5_url
    if args.create_zones_map:
        createZonesMap(args.geom_file, args.zones_file)
    if not os.path.exists(args.cover_file):
        raise ValueError("File not found: %s" % args.cover_file)
    if os.path.isdir(args.cover_file):
        cover_dir = args.cover_file
        print("Iterating content of: %s" % cover_dir)
        files = os.listdir(cover_dir)
        for file in sorted(files):
            match = re.search(args.file_pattern, file)
            if not match:
                print("Filename '%s' does not match pattern. Skipping" % file)
                continue
            args.__setattr__("year", int(match.group(1)))
            args.__setattr__("cover_file", "%s/%s" % (cover_dir, file))
            print("Processing file %s, year %i" % (args.cover_file, args.year))
            run(args)
    else:
        if args.year is None:
            match = re.search(args.file_pattern, args.cover_file)
            if not match:
                raise ValueError("Filename '%s' does not match pattern. Skipping" % args.cover_file)
            args.__setattr__("year", int(match.group(1)))
        run(args)
    