"""Builds a concordance from 2023 electorates (2020 boundaries) to 2026
electorates (2025 boundaries), weighted by 2023 Census electoral population.

Each 2025 meshblock is placed in a 2020 and a 2025 general electorate, and a
2020 and a 2025 Māori electorate, by its representative point (a point
guaranteed to be inside it). Its general electoral population is counted
towards the general electorates and its Māori electoral population towards
the Māori electorates.

Stats NZ suppresses counts below six (shown as -999) and randomly rounds the
rest to base 3. Suppressed general counts are taken as 0: the known counts
already add up to slightly more than the published electorate totals.
Suppressed Māori counts hide 7.7% of the Māori electoral population, so each
2025 Māori electorate's gap (published total minus known counts) is spread
evenly over its suppressed meshblocks. See NOTES.md.

Needs geopandas (see README.md for the venv) and the Stats NZ layers in
data/statsnz/ (see README.md). Electorate numbers come from
results/2023/electorate_stats.csv and results/2026-prelim/electorate_stats.csv
(download.py), matched by name.

Writes results/concordance/electorates_2023_2026.csv: one row per (2023
electorate, 2026 electorate) pair that share population, with the population
and its share of each.
"""
import argparse
import csv
import glob
import os

import geopandas as gpd

STATSNZ_DIR = "data/statsnz"
POPULATION_LAYER = "2023-census-electoral-population-at-meshblock-level-2025-mes"
ELECTORATE_LAYERS = {
    # key: (folder, code field, population field in the electorate layer)
    "GED2020": ("general-electorates-2020", "GED2020_V1_00", None),
    "GED2025": ("general-electorates-2025", "GED2025_V1_00", "GENERAL_ELECTORAL_POPULATION"),
    "MED2020": ("maori-electorates-2020", "MED2020_V1_00", None),
    "MED2025": ("maori-electorates-2025", "MED2025_V1_00", "MAORI_ELECTORAL_POPULATION"),
}
ROLLS = [
    # roll, population field, 2023 layer, 2026 layer
    ("general", "General_Electoral_Population", "GED2020", "GED2025"),
    ("maori", "Maori_Electoral_Population", "MED2020", "MED2025"),
]
SUPPRESSED = -999
ELECTORATE_STATS = {"2023": "results/2023/electorate_stats.csv", "2026": "results/2026-prelim/electorate_stats.csv"}


def gpkg(folder):
    files = glob.glob(os.path.join(STATSNZ_DIR, folder, "*.gpkg"))
    if len(files) != 1:
        raise FileNotFoundError("expected one .gpkg in {0}, found {1}".format(
            os.path.join(STATSNZ_DIR, folder), len(files)))
    return files[0]


def read_elec_ids(filename):
    """Returns {electorate name: elec_id} from an electorate_stats.csv."""
    with open(filename, newline="", encoding="utf-8") as f:
        return {row["elec_name"]: int(row["elec_id"]) for row in csv.DictReader(f)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default="results/concordance/electorates_2023_2026.csv")
    args = parser.parse_args()

    meshblocks = gpd.read_file(gpkg(POPULATION_LAYER))
    if meshblocks.MB2025_V1_00.duplicated().any():
        raise ValueError("duplicate meshblock codes")
    points = meshblocks.set_geometry(meshblocks.geometry.representative_point())[["MB2025_V1_00", "geometry"]]

    names = {}      # key -> {code: name}
    published = {}  # key -> {code: published electoral population}
    for key, (folder, code, pop_field) in ELECTORATE_LAYERS.items():
        layer = gpd.read_file(gpkg(folder))
        if layer.crs != meshblocks.crs:
            raise ValueError("{0} is in {1}, but meshblocks are in {2}".format(key, layer.crs, meshblocks.crs))
        names[key] = dict(zip(layer[code], layer[code + "_NAME"]))
        if pop_field:
            published[key] = dict(zip(layer[code], layer[pop_field]))
        joined = gpd.sjoin(points, layer[[code, "geometry"]], how="left", predicate="within")
        counts = joined.groupby("MB2025_V1_00")[code].count()
        if (counts != 1).any():
            raise ValueError("{0}: {1} meshblocks aren't in exactly one electorate".format(key, (counts != 1).sum()))
        meshblocks[key] = joined.set_index("MB2025_V1_00")[code].reindex(meshblocks.MB2025_V1_00).values

    elec_ids = {year: read_elec_ids(f) for year, f in ELECTORATE_STATS.items()}
    rows = []
    for roll, pop_field, key_2023, key_2026 in ROLLS:
        pop = meshblocks[pop_field].astype(float)
        if ((pop < 0) & (pop != SUPPRESSED)).any():
            raise ValueError("{0}: negative counts other than {1}".format(pop_field, SUPPRESSED))
        suppressed = pop == SUPPRESSED
        pop = pop.where(~suppressed, 0.0)
        if roll == "maori":
            # Spread each 2025 Māori electorate's hidden population over its suppressed meshblocks.
            known = pop.groupby(meshblocks[key_2026]).sum()
            n_suppressed = suppressed.groupby(meshblocks[key_2026]).sum()
            gap = {code: published[key_2026][code] - known[code] for code in known.index}
            if any(g < 0 for g in gap.values()):
                raise ValueError("Māori electorate with known counts above its published total")
            per_meshblock = meshblocks[key_2026].map({c: gap[c] / n_suppressed[c] for c in gap})
            pop = pop.where(~suppressed, per_meshblock)

        print("{0} roll: {1:,} meshblocks suppressed; total population {2:,.0f}".format(
            roll, suppressed.sum(), pop.sum()))
        totals_2026 = pop.groupby(meshblocks[key_2026]).sum()
        diff = {c: totals_2026[c] - published[key_2026][c] for c in totals_2026.index}
        worst = max(diff, key=lambda c: abs(diff[c]))
        print("  2026 electorate totals vs published: largest difference {0:+.0f} ({1})".format(
            diff[worst], names[key_2026][worst]))

        overlap = pop.groupby([meshblocks[key_2023], meshblocks[key_2026]]).sum()
        overlap = overlap[overlap > 0]
        totals_2023 = overlap.groupby(level=0).sum()
        totals_2026 = overlap.groupby(level=1).sum()
        for (code_2023, code_2026), population in overlap.items():
            name_2023 = names[key_2023][code_2023]
            name_2026 = names[key_2026][code_2026]
            rows.append([roll, elec_ids["2023"][name_2023], name_2023, elec_ids["2026"][name_2026], name_2026,
                         population, population / totals_2023[code_2023], population / totals_2026[code_2026]])

    rows.sort(key=lambda r: (r[3], -r[5]))
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["roll", "elec_id_2023", "elec_name_2023", "elec_id_2026", "elec_name_2026",
                         "population", "share_of_2023", "share_of_2026"])
        for r in rows:
            writer.writerow(r[:5] + ["{0:.0f}".format(r[5]), "{0:.6f}".format(r[6]), "{0:.6f}".format(r[7])])
    print("wrote {0} ({1} rows)".format(args.output, len(rows)))


if __name__ == "__main__":
    main()
