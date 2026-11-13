#!/usr/bin/env python3
import argparse
import datetime
import os
from pathlib import Path
import re
import sys
import tempfile
import subprocess

import grass.script as gs

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
    HOST_3H = Path(args.host_3h)
    HOST_1D = Path(args.host_1d)

    print("host: %s" % HOST)
    print("emision: %s" % args.emision)

    tmpdir = tempfile.mkdtemp(prefix="agrega_cosmo_tmp_")

    files = sorted(
        name
        for name in os.listdir(HOST)
        if f"PLATA_{args.emision}{args.inicializacion}" in name
        and re.match(r".*\.grb$", name)
    )

    for file in files:
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

    gs.mapcalc("prev_3h = 0", overwrite=True)
    gs.mapcalc("prev_d = 0", overwrite=True)

    step_3h = 3
    step_diario = 36

    tif_files = sorted(
        name
        for name in os.listdir(tmpdir)
        if f"PLATA_{args.emision}{args.inicializacion}" in name
    )

    for index, raster in enumerate(tif_files, start=1):
        if index == step_3h:
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
            step_3h += 3

            if index >= args.cut_diario and index == step_diario:
                gs.mapcalc(f"acum_diario = {raster} - prev_d", overwrite=True)
                gs.mapcalc(f"prev_d = {raster}", overwrite=True)
                gs.run_command(
                    "r.out.gdal",
                    input="acum_diario",
                    output=str(HOST_1D / raster),
                    overwrite=True,
                    nodata=args.nodata,
                )
                step_diario += 24

            gs.run_command("g.remove", type="raster", name=raster, flags="f")


if __name__ == "__main__":
    main()
