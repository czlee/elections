"""Exports simplified 2025 electorate boundaries, clipped to land, as TopoJSON
for the site's map (site/src/lib/data/electorates-2025.topo.json). Needs the
venv (geopandas), Node with the site's dev dependencies (mapshaper), and in
data/statsnz/:

  - general-electorates-2025, maori-electorates-2025 (as for concordance.py)
  - a clipped layer covering all land, used as a land mask: any folder
    matching LAND_GLOB, e.g. "Regional Council 2025 Clipped" from Datafinder.

The electorate layers include sea out to the territorial limit, and
Datafinder has no clipped electorate layer, so each electorate is intersected
with the dissolved land mask. Without a land mask (--no-clip) the unclipped
shapes are used, for testing.

Coordinates stay in NZTM (EPSG:2193) metres; the site draws them with an
identity projection. The Chatham Islands (east of CHATHAMS_X) are dropped
from the main map.
"""
import argparse
import glob
import os
import subprocess
import tempfile

import geopandas as gpd

STATSNZ_DIR = "data/statsnz"
LAYERS = {
    "general": ("general-electorates-2025", "GED2025_V1_00_NAME"),
    "maori": ("maori-electorates-2025", "MED2025_V1_00_NAME"),
}
LAND_GLOB = "*clipped*"
CHATHAMS_X = 2200000  # NZTM easting; the Chathams are around 2.4M
SIMPLIFY_M = 250  # mapshaper Visvalingam, tolerance in metres
MIN_ISLAND_KM2 = 4  # islands smaller than this are dropped (unless it's an electorate's only part)
OUTPUT = "site/src/lib/data/electorates-2025.topo.json"


def gpkg(folder):
    files = glob.glob(os.path.join(STATSNZ_DIR, folder, "*.gpkg"))
    if len(files) != 1:
        raise FileNotFoundError("expected one .gpkg in {0}, found {1}".format(folder, files))
    return files[0]


def land_mask():
    folders = [os.path.basename(f) for f in glob.glob(os.path.join(STATSNZ_DIR, LAND_GLOB)) if os.path.isdir(f)]
    if len(folders) != 1:
        raise FileNotFoundError("expected one land-mask folder matching {0} in {1}, found {2}".format(
            LAND_GLOB, STATSNZ_DIR, folders))
    land = gpd.read_file(gpkg(folders[0])).to_crs(2193)
    print("land mask: {0} ({1} features)".format(folders[0], len(land)))
    return land.union_all()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-clip", action="store_true", help="skip the land mask (for testing)")
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()

    land = None if args.no_clip else land_mask()
    with tempfile.TemporaryDirectory() as tmp:
        inputs = []
        for roll, (folder, name_col) in LAYERS.items():
            layer = gpd.read_file(gpkg(folder)).to_crs(2193)
            layer = layer[[name_col, "geometry"]].rename(columns={name_col: "name"})
            if land is not None:
                layer["geometry"] = layer.geometry.intersection(land)
            # Drop the Chatham Islands (part of Wellington Bays and Te Tai Tonga).
            # Keep polygons only: the intersection can leave line and point slivers.
            parts = layer.explode(index_parts=False)
            parts = parts[parts.geom_type == "Polygon"]
            parts = parts[parts.geometry.centroid.x < CHATHAMS_X]
            layer = parts.dissolve(by="name", as_index=False)
            path = os.path.join(tmp, roll + ".geojson")
            layer.to_file(path, driver="GeoJSON")
            inputs.append(path)
            print("{0}: {1} electorates".format(roll, len(layer)))
        # Simplify with shared borders kept, and write both layers into one TopoJSON.
        cmd = ["npx", "mapshaper", "-i", *inputs, "combine-files", "snap",
               "-simplify", "interval={0}".format(SIMPLIFY_M), "weighted", "keep-shapes",
               "-filter-islands", "min-area={0}".format(MIN_ISLAND_KM2 * 1e6), "remove-empty",
               "-clean",
               "-o", "format=topojson", "quantization=20000",
               os.path.abspath(args.output)]
        subprocess.run(cmd, check=True, cwd="site")
    print("wrote {0} ({1:,} bytes)".format(args.output, os.path.getsize(args.output)))


if __name__ == "__main__":
    main()
