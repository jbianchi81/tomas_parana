import os
import datetime
import pandas
from a5client import client
import argparse
#!/usr/bin/env python3
import os
import tempfile
import shutil

defaults = {
    "dt": datetime.timedelta(days=1),
    "coef": 86400,
    "method": "average",
    "zones_file": "data/areas_pluvio.tif",
    "offset_hours": 9
}

def zonalMeans(zones_file : str, cover_file : str, csvdir : str, coef : int, method: str):
    import grass.script as gs

    # Ensure output directory exists
    os.makedirs(csvdir, exist_ok=True)

    # --- Define region ---
    gs.run_command("g.region", n=-10, s=-40, e=-40, w=-70, res=0.05)

    # --- Load zones raster ---
    gs.run_command("r.in.gdal", input=zones_file, output="areas_pluvio", overwrite=True, flags="oq")

    # Convert to int and mask out 0
    gs.mapcalc("areas = int(areas_pluvio)", overwrite=True)
    gs.run_command("r.null", map="areas", setnull=0)

    # --- Load cover raster (multiband) ---
    gs.run_command("r.in.gdal", input=cover_file, output="cover", overwrite=True, flags="oq")

    # --- Iterate over each band ---
    cover_maps = gs.list_grouped("raster", pattern="cover.*")[gs.gisenv()["MAPSET"]]

    for cover_map in sorted(cover_maps):
        print(f"Processing {cover_map} ...")
        map_index = cover_map.split(".")[-1]  # e.g. 'cover.12' → '12'

        # Rescale
        gs.mapcalc(f"cover_scaled = {coef} * {cover_map}", overwrite=True)

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
        offset_hours : int = 0,
        upload : bool = False):
    series_areales : pandas.DataFrame = getSeries(fuentes_id)
    obs = [] # pandas.DataFrame(columns={"series_id": int, "valor": float, "timestart": datetime, "timeend": datetime})
    files = os.listdir(dirname)
    for file in files:
        filepath = "%s/%s" % (dirname, file)
        obs.append(parseCSVFile(filepath, year, series_areales, dt, offset_hours))
    allobs = pandas.concat(obs, ignore_index=True)
    if output is not None:
        allobs.to_json(output,orient="records", date_format='iso', indent=2)
    if upload:
        for series_id, group in allobs.groupby("series_id"):
            observaciones = group.set_index("timestart")
            print("Uploading series_id: %i" % series_id)
            client.createObservaciones(observaciones, series_id, tipo="areal")
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
    if not args.skip_grass_process:
        zonalMeans(args.zones_file, args.cover_file, args.csvdir, args.coef, args.method)
    readDir(args.csvdir, args.year, args.fuentes_id, args.dt, args.output, args.offset_hours, args.upload)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cover_file", type=str)
    parser.add_argument("output", type=str)
    parser.add_argument("-y","--year", type=int, required=True)
    parser.add_argument("-f","--fuentes_id", type=int, required=True)
    parser.add_argument("-D","--csvdir", type=str)
    parser.add_argument("-z","--zones_file", type=str, default=defaults["zones_file"])
    parser.add_argument("-d","--dt", type=datetime.timedelta, default=defaults["dt"])
    parser.add_argument("-o","--offset_hours", type=int, default=defaults["offset_hours"])
    parser.add_argument("-c","--coef", type=float, default=defaults["coef"])
    parser.add_argument("-m","--method", type=str, default=defaults["method"])
    parser.add_argument("-u","--upload",action="store_true")
    parser.add_argument("-S","--skip_grass_process",action="store_true")
    args = parser.parse_args()
    if args.csvdir is None:
        args.__setattr__("csvdir",tempfile.mkdtemp(prefix="zonal_means_tmp_"))
        print(f"🧩 Using temporary directory: {args.csvdir}")
        is_tmpdir = True
    else:
        is_tmpdir = False
    try:   
        run(args)
    finally:
        if is_tmpdir:
            # --- Clean up temporary directory ---
            print(f"🧹 Cleaning up temporary directory: {args.csvdir}")
            shutil.rmtree(args.csvdir, ignore_errors=True)
    