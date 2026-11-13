# Scripts for collating NZ elections data

© Chuan-Zheng Lee 2026

This is a collection of Python scripts that download and parse CSV files from the New Zealand Electoral Commission's results website, https://electionresults.govt.nz/. It produces aggregated statistics that aren't already presented in the statistics published by the Electoral Commission.

My previous scripts have been moved to [czlee/elections-2020](https://github.com/czlee/elections-2020).

## Setup

The scripts that download and project results (`download.py`,
`scrape_wayback_prelim.py`, `project_specials.py`, `seats.py`) use only the
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
| General Electorates 2020 | [104580](https://datafinder.stats.govt.nz/layer/104580-general-electorates-2020/) |
| Māori Electorates 2020 | [104579](https://datafinder.stats.govt.nz/layer/104579-maori-electorates-2020/) |
| General Electorates 2025 | [122741](https://datafinder.stats.govt.nz/layer/122741-general-electorates-2025/) |
| Māori Electorates 2025 | [122742](https://datafinder.stats.govt.nz/layer/122742-maori-electorates-2025/) |
| 2023 Census electoral population at meshblock level (2025 Meshblock) | [121975](https://datafinder.stats.govt.nz/layer/121975-2023-census-electoral-population-at-meshblock-level-2025-meshblock/) |

## Running the 2026 projections

```
python3 download.py --election 2023          # 2023 official results
python3 download.py                          # 2026 preliminary results
python3 scrape_wayback_prelim.py             # 2023 preliminary count (slow: Wayback Machine)
python3 project_specials.py                  # national projection
venv/bin/python concordance.py               # 2023 -> 2026 electorates (needs data/statsnz/)
python3 project_electorates.py               # per-electorate projection
```

Outputs are in `results/` (gitignored). `project_electorates.py` reads the
national projection's party votes for seat allocation, so run
`project_specials.py` first.
