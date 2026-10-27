#!/usr/bin/env python3
"""Create GRASS probability-of-exceedance maps from raster ensemble members."""

import argparse
import glob
import math
import re
import uuid
from pathlib import Path
from typing import Any


DEFAULT_CATEGORY_CUTS = (5.0, 35.0, 65.0, 95.0)
DEFAULT_COLOR_RULES = Path("public/color_rules/prob_exceed")
DEFAULT_THESHOLDS = (10, 50, 100)

def threshold_tag(threshold: float) -> str:
    value = format(threshold, "g")
    return value.replace("-", "m").replace(".", "_").replace("+", "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import matching single-band GDAL rasters into the active GRASS "
            "mapset and calculate per-cell probability of exceeding thresholds."
        )
    )
    parser.add_argument(
        "pattern",
        help='Input file glob, for example "data/ensemble/member_*.tif".',
    )
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=DEFAULT_THESHOLDS,
        help="One or more values; exceedance is defined as raster value > threshold.",
    )
    parser.add_argument(
        "--output-prefix",
        required=True,
        help="Prefix for output raster names.",
    )
    parser.add_argument(
        "--color-rules",
        type=Path,
        default=DEFAULT_COLOR_RULES,
        help="GRASS r.colors rules file for the five categorized classes.",
    )
    parser.add_argument(
        "--category-cuts",
        type=float,
        nargs="+",
        default=DEFAULT_CATEGORY_CUTS,
        # metavar=("CUT1", "CUT2", "CUT3", "CUT4"),
        help="Increasing probability cutoffs defining color categories.",
    )
    parser.add_argument(
        "--gdal-output-dir",
        required=True,
        type=Path,
        help="Directory for mandatory percentage GeoTIFF exports.",
    )
    parser.add_argument(
        "--png-output-dir",
        type=Path,
        help="Optional directory for PNG previews of the categorized maps.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing existing GRASS maps and exported files.",
    )
    parser.add_argument(
        "--keep-temp-maps",
        action="store_true",
        help="Don't delete temporary GRASS maps.",
    )
    return parser.parse_args()


def category_expression(
    probability_map: str,
    class_map: str,
    cuts: list[float],
) -> str:
    expression = str(len(cuts) + 1)
    for category, cutoff in reversed(list(enumerate(cuts, start=1))):
        expression = f"if({probability_map} <= {cutoff!r}, {category}, {expression})"
    return f"{class_map} = if(isnull({probability_map}), null(), {expression})"


def export_png(
        gs: Any, 
        output_map: str, 
        output_path: Path, 
        overwrite: bool, 
        category_cuts : list=list(DEFAULT_CATEGORY_CUTS),
        title : str="Prob") -> None:
    gs.run_command(
        "d.mon",
        start="cairo",
        output=str(output_path),
        overwrite=overwrite,
    )
    try:
        gs.run_command("d.rast", map=output_map)
        gs.run_command("d.legend",raster=output_map,label_values=",".join([str(c) for c in category_cuts]))
        gs.run_command("d.text",text=title,color="black")
    finally:
        gs.run_command("d.mon", stop="cairo")


def main() -> None:
    args = parse_args()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", args.output_prefix):
        raise ValueError("Output prefix must start with a letter and contain only letters, digits, or underscores.")
    if not args.thresholds or any(not math.isfinite(value) for value in args.thresholds):
        raise ValueError("Thresholds must be finite numeric values.")
    if len(set(args.thresholds)) != len(args.thresholds):
        raise ValueError("Threshold values must be unique.")
    if any(not math.isfinite(value) for value in args.category_cuts):
        raise ValueError("Category cuts must be finite numeric values.")
    if list(args.category_cuts) != sorted(set(args.category_cuts)):
        raise ValueError("Category cuts must be strictly increasing.")
    if not args.color_rules.is_file():
        raise FileNotFoundError(f"Color rules file not found: {args.color_rules}")

    input_files = sorted(
        path for path in glob.glob(args.pattern) if Path(path).is_file()
    )
    if not input_files:
        raise FileNotFoundError(f"No input files matched pattern: {args.pattern}")

    output_names = [
        f"{args.output_prefix}_exceed_{threshold_tag(value)}"
        for value in args.thresholds
    ]
    if len(set(output_names)) != len(output_names):
        raise ValueError("Thresholds produce duplicate GRASS output names.")
    if any(len(name) > 63 for name in output_names):
        raise ValueError("Output raster names must not exceed 63 characters.")

    import grass.script as gs

    args.gdal_output_dir.mkdir(parents=True, exist_ok=True)
    if args.png_output_dir is not None:
        args.png_output_dir.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex[:8]
    member_maps = [f"ens_{run_id}_{index:05d}" for index in range(len(input_files))]
    temporary_maps: list[str] = []

    try:
        for filepath, raster_map in zip(input_files, member_maps):
            print(f"Importing {filepath} as {raster_map}")
            gs.run_command(
                "r.in.gdal",
                input=filepath,
                output=raster_map,
                band=1,
            )
            temporary_maps.append(raster_map)

        gs.run_command("g.region", raster=member_maps[0])

        for threshold, output_map in zip(args.thresholds, output_names):
            valid_map = f"valid_{run_id}_{threshold_tag(threshold)}"
            exceed_map = f"exceed_{run_id}_{threshold_tag(threshold)}"

            valid_terms = [
                f"if(isnull({raster_map}), 0, 1)" for raster_map in member_maps
            ]
            exceed_terms = [
                f"if(isnull({raster_map}), 0, if({raster_map} > {threshold!r}, 1, 0))"
                for raster_map in member_maps
            ]
            gs.mapcalc(
                f"{valid_map} = {' + '.join(valid_terms)}",
                overwrite=True,
            )
            temporary_maps.append(valid_map)
            gs.mapcalc(
                f"{exceed_map} = {' + '.join(exceed_terms)}",
                overwrite=True,
            )
            temporary_maps.append(exceed_map)
            gs.mapcalc(
                f"{output_map} = if({valid_map} > 0, "
                f"100.0 * {exceed_map} / {valid_map}, null())",
                overwrite=args.overwrite,
            )
            # class_map = f"class_{run_id}_{threshold_tag(threshold)}"
            # gs.mapcalc(
            #     category_expression(
            #         output_map,
            #         class_map,
            #         list(args.category_cuts),
            #     ),
            #     overwrite=True,
            # )
            # temporary_maps.append(class_map)
            gs.run_command(
                "r.colors",
                map=output_map,
                rules=str(args.color_rules),
            )
            gdal_path = args.gdal_output_dir / f"{output_map}.tif"
            gs.run_command(
                "r.out.gdal",
                input=output_map,
                output=str(gdal_path),
                format="GTiff",
                type="Float32",
                overwrite=args.overwrite,
                flags="f"                
            )
            if args.png_output_dir is not None:
                png_path = args.png_output_dir / f"{output_map}.png"
                export_png(
                    gs, 
                    output_map, 
                    png_path, 
                    args.overwrite, 
                    args.category_cuts,
                    "Prob. (PP>%02d mm)" % threshold
                )
            print(f"Created {output_map} for threshold {threshold:g}")
    finally:
        if temporary_maps and not args.keep_temp_maps:
            gs.run_command(
                "g.remove",
                type="raster",
                name=",".join(temporary_maps),
                flags="f",
            )


if __name__ == "__main__":
    main()
