#!/usr/bin/env python3
"""Create a precipitation match danger map in the active GRASS mapset."""

import argparse
import math
from pathlib import Path
import sys


THRESHOLDS = (0, 10, 50, 80, 100)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import two precipitation rasters, calculate matching threshold "
            "areas, and export a danger map from the active GRASS mapset."
        )
    )
    parser.add_argument(
        "input_1",
        nargs="?",
        default="data/match/input_1.tif",
        help="First input GeoTIFF (default: data/match/input_1.tif).",
    )
    parser.add_argument(
        "input_2",
        nargs="?",
        default="data/match/input_2.tif",
        help="Second input GeoTIFF (default: data/match/input_2.tif).",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=0.07,
        help="Region resolution in degrees (default: 0.07).",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=7,
        help="Odd r.neighbors window size (default: 7).",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.5,
        help="Minimum neighborhood fraction for a threshold area (default: 0.5).",
    )
    parser.add_argument(
        "--title",
        default="Match QPF INA (COSMO+GFS)",
        help="Danger map legend title.",
    )
    parser.add_argument(
        "--output",
        default="data/match/DangerMap.tif",
        help="Output GeoTIFF path (default: data/match/DangerMap.tif).",
    )
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=THRESHOLDS,
        help="List of thresholds to evaluate (default: 0 10 50 80 100).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not math.isfinite(args.resolution) or args.resolution <= 0:
        raise ValueError("Resolution must be a finite number greater than zero.")
    if not math.isfinite(args.fuzzy_threshold):
        raise ValueError("Fuzzy threshold must be a finite number.")
    if args.window_size <= 0 or args.window_size % 2 == 0:
        raise ValueError("Window size must be a positive odd integer.")

    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    import grass.script as gs
    from grass.exceptions import CalledModuleError

    gs.run_command(
        "g.region", res=args.resolution, n=-14, s=-45, w=-70, e=-40
    )
    for raster_path, raster_name in (
        (args.input_1, "input_1"),
        (args.input_2, "input_2"),
    ):
        try:
            gs.run_command(
                "r.in.gdal",
                input=raster_path,
                output=raster_name,
                overwrite=True,
                flags="o",
            )
        except CalledModuleError as exc:
            print("Problema al importar a GRASS. Abortando.", file=sys.stderr)
            raise SystemExit(2) from exc

    for threshold in args.thresholds:
        try:
            gs.mapcalc(
                "ThresholdArea = "
                f"if(and(input_1 > {threshold}, input_2 > {threshold}))",
                overwrite=True,
            )
        except CalledModuleError as exc:
            print(
                "Problema para detectar Area. Chequear input_1 o input_2. "
                "Abortando.",
                file=sys.stderr,
            )
            raise SystemExit(2) from exc

        try:
            gs.run_command(
                "r.neighbors",
                input="ThresholdArea",
                size=args.window_size,
                output="TNeig",
                overwrite=True,
            )
        except CalledModuleError as exc:
            print("Problema para generar FuzzyMap. Abortando.", file=sys.stderr)
            raise SystemExit(2) from exc

        try:
            gs.mapcalc(
                f"TNeig_{threshold} = "
                f"if(TNeig > {args.fuzzy_threshold}, {threshold}, null())",
                overwrite=True,
            )
        except CalledModuleError as exc:
            print(
                "Problema al ajustar superficie final. Abortando.",
                file=sys.stderr,
            )
            raise SystemExit(2) from exc

        try:
            gs.run_command(
                "r.to.vect",
                input=f"TNeig_{threshold}",
                type="area",
                output="ThreatZone",
                flags="s",
                overwrite=True,
            )
        except CalledModuleError:
            print("Problema al transformar a vectorial.", file=sys.stderr)
        try:
            gs.run_command(
                "v.out.ogr",
                input="ThreatZone",
                format="GeoJSON",
                output=f"{output_dir}/ThreatZone_{threshold}.geojson",
                overwrite=True,
            )
        except CalledModuleError:
            print("Problema al exportar GeoJSON.", file=sys.stderr)

    gs.run_command(
        "r.patch",
        input=",".join(f"TNeig_{threshold}" for threshold in reversed(args.thresholds)),
        output="DangerMap",
        overwrite=True,
    )
    gs.run_command("r.colors", map="DangerMap", rules="./public/color_rules/danger_map_colors.txt")
    gs.run_command("d.mon", start="cairo", output=str(output_dir / "DangerMap.png"), width=1024, height=960, overwrite=True)
    gs.run_command("d.erase")
    gs.run_command("d.rast", map="DangerMap")
    gs.run_command("d.vect", map="lim_prov", type="boundary", color="grey")
    gs.run_command("d.vect", map="sa_limites_administrativos", type="boundary", color="black")
    gs.run_command(
        "d.vect", map="cdp", type="boundary", color="black", width=2
    )
    gs.run_command(
        "d.legend",
        raster="DangerMap",
        title=f"{args.title}*",
        at="98,83,4,1",
        use="10,50,80,100",
        flags="b",
        lines=10,
        title_fontsize=10,
        fontsize=8,
        units="mm",
        range="0,100",
    )
    gs.run_command(
        "d.text",
        text="(*) Valor umbral inferior de categoria",
        at="50,5",
        size=1,
        color="black",
        align="lr",
    )
    gs.run_command("d.mon", stop="cairo")
    gs.run_command(
        "r.out.gdal",
        input="DangerMap",
        output=args.output,
        format="GTiff",
        type="UInt16",
        overwrite=True,
    )


if __name__ == "__main__":
    main()
