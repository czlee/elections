"""Lays out the 2026 (2025-boundary) electorates as an equal-area hex map for
the site, written to site/src/lib/data/hexmap.json. Needs the venv
(geopandas) and the Stats NZ 2025 electorate layers in data/statsnz/.

General and Māori electorates are laid out separately (they overlap), each by:
  1. taking each electorate's population-weighted centre (2023 Census
     electoral population by 2025 meshblock, EPSG:2193);
  2. scaling so the whole layout is about ROWS hex rows tall;
  3. spreading the points apart so none are closer than one hex, with a weak
     pull back to their true positions (dense Auckland pushes outwards);
  4. assigning each electorate to a distinct cell of a pointy-top hex grid,
     minimising the total squared distance (Hungarian algorithm).

The result is a starting point: positions can be hand-tuned with OVERRIDES.
"""
import argparse
import glob
import json
import math
import os

import geopandas as gpd
import numpy as np

STATSNZ_DIR = "data/statsnz"
LAYERS = {
    "general": ("general-electorates-2025", "GED2025_V1_00_NAME", 17),
    "maori": ("maori-electorates-2025", "MED2025_V1_00_NAME", 5),
}
MESHBLOCKS = "2023-census-electoral-population-at-meshblock-level-2025-mes"
SQRT3 = math.sqrt(3)
RANK_BLEND = 0.35  # 0 = true north-south positions, 1 = evenly spaced by rank
OVERRIDES = {}  # electorate name -> (q, r), applied after the automatic layout


def population_centres(layer, meshblocks, column):
    """Population-weighted mean of meshblock points in each electorate. (The
    polygons include sea, so geometric centres are off: Wellington Bays'
    largest part is the Chatham Islands.) Suppressed counts (-999) count as 0."""
    joined = gpd.sjoin(meshblocks, layer[["geometry"]], predicate="within")
    w = joined[column].clip(lower=0)
    joined = joined.assign(w=w, wx=w * joined.geometry.x, wy=w * joined.geometry.y)
    sums = joined.groupby("index_right")[["w", "wx", "wy"]].sum()
    return np.column_stack([sums.loc[layer.index, "wx"] / sums.loc[layer.index, "w"],
                            sums.loc[layer.index, "wy"] / sums.loc[layer.index, "w"]])


def hex_centre(q, r):
    """Pointy-top axial coordinates to Cartesian, neighbour distance sqrt(3)."""
    return SQRT3 * (q + r / 2), 1.5 * r


def spread(points, iterations=800):
    """Pushes points apart to at least SQRT3, with a weak pull home."""
    home = points.copy()
    p = points.copy()
    for _ in range(iterations):
        d = p[:, None, :] - p[None, :, :]
        dist = np.sqrt((d ** 2).sum(-1)) + np.eye(len(p))
        overlap = np.clip(SQRT3 * 1.05 - dist, 0, None)
        np.fill_diagonal(overlap, 0)
        push = (d / dist[..., None] * overlap[..., None]).sum(1) * 0.25
        p += push + (home - p) * 0.02
    return p


def hungarian(cost):
    """Minimum-cost assignment of rows to distinct columns (rows <= columns).
    Returns a list: column assigned to each row."""
    n, m = cost.shape
    INF = float("inf")
    u, v = [0.0] * (n + 1), [0.0] * (m + 1)
    p, way = [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    result = [0] * n
    for j in range(1, m + 1):
        if p[j]:
            result[p[j] - 1] = j - 1
    return result


def layout(names, xy, rows):
    # Scale so the layout is about `rows` hex rows tall; flip y (SVG y goes down).
    y_range = xy[:, 1].max() - xy[:, 1].min()
    scale = (1.5 * rows) / y_range
    pts = np.column_stack([(xy[:, 0] - xy[:, 0].min()) * scale, (xy[:, 1].max() - xy[:, 1]) * scale])
    # Even out north-south density: blend each y with its rank, spread over the same range.
    rank = np.argsort(np.argsort(pts[:, 1])) / max(1, len(pts) - 1) * pts[:, 1].max()
    pts[:, 1] = (1 - RANK_BLEND) * pts[:, 1] + RANK_BLEND * rank
    pts = spread(pts)
    # Candidate cells: every hex within 2 units of a spread point.
    cells = {}
    for x, y in pts:
        r0 = round(y / 1.5)
        for r in range(r0 - 2, r0 + 3):
            q0 = round(x / SQRT3 - r / 2)
            for q in range(q0 - 2, q0 + 3):
                cells[(q, r)] = hex_centre(q, r)
    keys = list(cells)
    centres = np.array([cells[k] for k in keys])
    cost = ((pts[:, None, :] - centres[None, :, :]) ** 2).sum(-1)
    assigned = hungarian(cost)
    out = {name: keys[c] for name, c in zip(names, assigned)}
    out.update({n: tuple(v) for n, v in OVERRIDES.items() if n in out})
    return out


def ascii_preview(positions, width=3):
    qs = {}
    for name, (q, r) in positions.items():
        qs[(q, r)] = name
    rs = [r for _, r in qs]
    xs = [2 * q + r for q, r in qs]
    lines = []
    for r in range(min(rs), max(rs) + 1):
        row = [" " * width] * (max(xs) - min(xs) + 1)
        for (q, rr), name in qs.items():
            if rr == r:
                row[2 * q + r - min(xs)] = name[:width].ljust(width)
        lines.append("".join(row).rstrip())
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default="site/src/lib/data/hexmap.json")
    args = parser.parse_args()

    meshblocks = gpd.read_file(glob.glob(os.path.join(STATSNZ_DIR, MESHBLOCKS, "*.gpkg"))[0])
    meshblocks["geometry"] = meshblocks.geometry.representative_point()
    pop_col = {"general": "General_Electoral_Population", "maori": "Maori_Electoral_Population"}
    result = {}
    for roll, (folder, name_col, rows) in LAYERS.items():
        files = glob.glob(os.path.join(STATSNZ_DIR, folder, "*.gpkg"))
        layer = gpd.read_file(files[0])
        xy = population_centres(layer, meshblocks, pop_col[roll])
        positions = layout(list(layer[name_col]), xy, rows)
        print("{0}:\n{1}\n".format(roll, ascii_preview(positions)))
        # Normalise so the minimum q and r are 0 within each roll.
        min_r = min(r for _, r in positions.values())
        positions = {n: (q + (min_r - min_r), r - min_r) for n, (q, r) in positions.items()}
        min_x = min(2 * q + r for q, r in positions.values())
        shift = -(min_x // 2) if min_x % 2 == 0 else -((min_x - 1) // 2)
        result[roll] = {n: [q + shift, r] for n, (q, r) in sorted(positions.items())}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print("wrote " + args.output)


if __name__ == "__main__":
    main()
