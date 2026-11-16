#!/usr/bin/env python3
import argparse
import datetime
import os
from pathlib import Path
import re
import sys
import tempfile
import subprocess
from typing import List

import grass.script as gs

def date_from_yyyymmddhh(s):
    return datetime.datetime.strptime(s, '%Y%m%d%H').replace(tzinfo=datetime.timezone.utc)

def date_range(start : datetime.datetime, end : datetime.datetime, step_hours=3, offset_hours=0):
    d = start + datetime.timedelta(hours=offset_hours)
    result : List[datetime.datetime]= []
    while d <= end:
        result.append(d)
        d += datetime.timedelta(hours=step_hours)
    return result

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--emision",
        default=datetime.date.today().strftime("%Y%m%d"),
        help="Emission date in YYYYMMDD format",
    )
    parser.add_argument("--inicializacion", default="00")
    parser.add_argument("--null", dest="nodata", default="-9999")
    parser.add_argument("--cut-diario", type=int, default=12)
    parser.add_argument("--host", default="data/cosmo")
    parser.add_argument("--host-3h", default="data/cosmo/3_horario")
    parser.add_argument("--host-1d", default="data/cosmo/diario")    

    args = parser.parse_args()

    year = args.emision[0:4]
    month = args.emision[4:6]

    HOST = Path(args.host, year, month)
    HOST_3H = Path(args.host_3h, year, month)
    HOST_1D = Path(args.host_1d, year, month)

    HOST_3H.mkdir(parents=True, exist_ok=True)
    HOST_1D.mkdir(parents=True, exist_ok=True)

    print("host: %s" % HOST)
    print("emision: %s" % args.emision)

    tmpdir = tempfile.mkdtemp(prefix="agrega_cosmo_tmp_")

    files = sorted(
        name
        for name in os.listdir(HOST)
        if f"PLATA_{args.emision}{args.inicializacion}" in name
        and re.match(r".*_\d{10}\.grb$", name)
    )

    start_date = date_from_yyyymmddhh(f"{args.emision}{args.inicializacion}")
    end_date = start_date + datetime.timedelta(hours=174)
    
    timestamps = [d for d in date_range(start_date, end_date, 3, 2)]
    
    expected_files = [f"PLATA_{args.emision}{args.inicializacion}_{d.strftime('%Y%m%d%H')}.grb" for d in timestamps]

    tif_files = []

    for file in expected_files:

        if not Path(HOST, file).is_file():
            raise ValueError("No se encontró el archivo %s" % file)

        out = file.replace(".grb",".tif")
        result = subprocess.run(["cp", Path(HOST, file), "sample.grb"], check=True)
        if result.returncode != 0:
            print("error al copiar archivo grb. Abortando")
            sys.exit(1)
        print(f"generando {out}")
        with open("sample.ctl", "w") as f:
            subprocess.run(["perl", "grib2ctl.pl", "-verf", "sample.grb"], check=True, stdout=f, text=True)
        subprocess.run(["gribmap", "-i", "sample.ctl"], check=False)        
        subprocess.run(["grads", "-bpcx", "run commands.grads"], check=False)
        subprocess.run(["cp", "sample.tif", Path(tmpdir, out)], check=True)
        tif_files.append(out)

    gs.mapcalc("prev_3h = 0", overwrite=True)
    gs.mapcalc("prev_d = 0", overwrite=True)

    # step_3h = 3
    # step_diario = 12

    # tif_files = sorted(
    #     name
    #     for name in os.listdir(tmpdir)
    #     if f"PLATA_{args.emision}{args.inicializacion}" in name
    # )

    files_3h = []
    files_1d = []

    for index, raster in enumerate(tif_files, start=0):
        timestamp = timestamps[index]
        print("timestamp: %s" % timestamp.strftime('%Y%m%d%H'))
        forecast_time = timestamp - start_date
        forecast_hours = int((forecast_time).seconds / 3600 + forecast_time.days * 24)

        # if index == step_3h:
        print("Importando %s" % Path(tmpdir, raster))
        gs.run_command(
            "r.in.gdal",
            input=Path(tmpdir, raster),
            output=raster,
            overwrite=True,
        )
        gs.run_command("g.region", raster=raster)
        gs.run_command("r.null", map=raster, setnull="-9.99e+08")
        gs.mapcalc(f"acum_3h = {raster} - prev_3h", overwrite=True)
        gs.mapcalc(f"prev_3h = {raster}", overwrite=True)
        gs.run_command(
            "r.out.gdal",
            input="acum_3h",
            output=str(HOST_3H / raster),
            overwrite=True,
            nodata=args.nodata,
        )
        files_3h.append(raster)
        # step_3h += 3

        if timestamp.hour == 11:
            print("acum diario")
            # if index == step_diario:
            if forecast_hours <= args.cut_diario:
                print("bajo el cut_diario")
                # if index <= args.cut_diario:
                gs.mapcalc(f"prev_d = {raster}", overwrite=True)
            else:
                print("Genera acum diario")
                gs.mapcalc(f"acum_diario = {raster} - prev_d", overwrite=True)
                gs.mapcalc(f"prev_d = {raster}", overwrite=True)
                gs.run_command(
                    "r.out.gdal",
                    input="acum_diario",
                    output=str(HOST_1D / raster),
                    overwrite=True,
                    nodata=args.nodata,
                )
                files_1d.append(raster)

        gs.run_command("g.remove", type="raster", name=raster, flags="f")

    with open(Path(HOST_3H, "index.csv"), "w") as f:
        f.write("\n".join(files_3h))
        f.close()
    with open(Path(HOST_1D, "index.csv"), "w") as f:
        f.write("\n".join(files_1d))
        f.close()

if __name__ == "__main__":
    main()
