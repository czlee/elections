# Scripts for collating NZ elections data

© Chuan-Zheng Lee 2026

This is a collection of Python scripts that download and parse CSV files from the New Zealand Electoral Commission's results website, https://electionresults.govt.nz/. It produces aggregated statistics that aren't already presented in the statistics published by the Electoral Commission.

My previous scripts have been moved to [czlee/elections-2020](https://github.com/czlee/elections-2020).

## Setup

The scripts that download and project results (everything in `scripts/` except
`concordance.py` and `export_boundaries.py`) use only the
Python standard library (Python 3.11 or later, for `tomllib`).

The electorate concordance (2023 → 2026 boundaries) needs geopandas. Install it
in a virtual environment:

```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### Stats NZ data

The concordance also needs these datasets from
[Stats NZ Datafinder](https://datafinder.stats.govt.nz/). They're free, but
you need an account to download them. Export each one as **GeoPackage**, in
**NZGD2000 / New Zealand Transverse Mercator 2000 (EPSG:2193)**, using the
full-resolution versions (not "clipped" or "generalised"). Datafinder can put
several layers into one zip; extract it into `data/statsnz/` (gitignored), which
gives one folder per layer:

| Dataset | Datafinder layer |
|---|---|
| General Electoral District 2014 (for 2017) | [104062](https://datafinder.stats.govt.nz/layer/104062-general-electoral-district-2014/) |
| Māori Electoral District 2014 (for 2017) | [104063](https://datafinder.stats.govt.nz/layer/104063-maori-electoral-district-2014/) |
| General Electorates 2020 | [104580](https://datafinder.stats.govt.nz/layer/104580-general-electorates-2020/) |
| Māori Electorates 2020 | [104579](https://datafinder.stats.govt.nz/layer/104579-maori-electorates-2020/) |
| General Electorates 2025 | [122741](https://datafinder.stats.govt.nz/layer/122741-general-electorates-2025/) |
| Māori Electorates 2025 | [122742](https://datafinder.stats.govt.nz/layer/122742-maori-electorates-2025/) |
| 2023 Census electoral population at meshblock level (2025 Meshblock) | [121975](https://datafinder.stats.govt.nz/layer/121975-2023-census-electoral-population-at-meshblock-level-2025-meshblock/) |
| Regional Council 2025 Clipped (map coastline only; `export_boundaries.py`) | [120945](https://datafinder.stats.govt.nz/layer/120945-regional-council-2025-clipped/) |

All are CC BY 4.0, credited in the site's footer.

## Layout

The scripts are in `scripts/`, and mirror `sites/`: the scripts that only one site uses are in
`scripts/<site>/`, and the ones several sites use (`download.py`, `parties.py`, `seats.py`,
`concordance.py`, `scrape_wayback_prelim.py`, `export_boundaries.py`) are in `scripts/`. Run them all
from the repository root, e.g. `python3 scripts/download.py`. The scripts in `scripts/<site>/` add
`scripts/` to `sys.path` to find the shared modules. `party_names.toml` and
`candidate_name_exceptions.toml` are at the root, and `/data` and `/results` are gitignored.

There are two projections of the 2026 special votes, each with its own site:

- `scripts/2026-projection/` is the main one: one special-vote multiplier per party. It's the one I've
  checked carefully. Its CSVs are in `results/projection-2026/`.
- `scripts/2026-projection-complicated/` is an experiment I haven't checked as rigorously: separate
  multipliers for overseas and domestic special votes, and the official count's revisions to ordinary
  votes. Its CSVs are in `results/projection-2026-complicated/`, so the two don't overwrite each other.

## Running the 2026 projections

```
python3 scripts/download.py --election 2023  # 2023 official results
python3 scripts/download.py                  # 2026 preliminary results
python3 scripts/scrape_wayback_prelim.py     # 2023 preliminary count (slow: Wayback Machine)
python3 scripts/2026-projection/project_specials.py      # national projection
venv/bin/python scripts/concordance.py       # 2023 -> 2026 electorates (needs data/statsnz/)
python3 scripts/2026-projection/project_electorates.py   # per-electorate projection
python3 scripts/2026-projection/export_site_data.py      # JSON for the site (sites/2026-projection/src/lib/data/)
venv/bin/python scripts/export_boundaries.py # map boundaries for the site (needs data/statsnz/ and sites/2026-projection/ npm install)
```

The experimental projection has the same three steps in `scripts/2026-projection-complicated/`, and also needs
`python3 scripts/2026-projection-complicated/download_specials.py -e 2023` first (special votes by category,
party and candidate; slow: Wayback Machine). See `sites/2026-projection-complicated/README.md`.

The visualisation site is in `sites/2026-projection/` (see `sites/2026-projection/README.md`); it's deployed to
https://czlee.nz/elections/2026-projection/ by GitHub Actions on pushes to `main`.

Outputs are in `results/` (gitignored). `project_electorates.py` reads the
national projection's party votes for seat allocation, so run
`project_specials.py` first.
