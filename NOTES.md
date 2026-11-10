# Notes

Working notes for this repo: facts we've established about the Electoral
Commission's results website, and (later) plans. Dates are when something was
checked; the site changes, so re-check anything old before relying on it.

## Facts

### Site access (checked 8–9 November 2026)

- **Everything except the XML feeds is blocked to scripts.** Cloudflare returns
  a 403 "Sorry, you have been blocked" page (about 4.8–6 KB of HTML) for the
  homepage, the `statistics/` pages and the per-voting-place CSVs, on both
  `www.electionresults.govt.nz` and `archive.electionresults.govt.nz`. Checked
  for 2002, 2014, 2017, 2020 and 2023. Claude's web-fetch tool, which runs from a
  different network, was blocked too, so it isn't specific to one IP address.
  Leaving out the User-Agent doesn't help.
- **The `/xml/` paths are reachable** with a custom User-Agent (we use
  `Elections Analysis`) or curl's default. **Python's default User-Agent
  (`Python-urllib/3.x`) gets a 403 even on `/xml/`**, so scripts must set one.
- **Use the main host, not the archive host.**
  `https://www.electionresults.govt.nz/electionresults_YYYY/xml/` serves files
  *and* directory listings. On `archive.electionresults.govt.nz` the same paths
  serve individual files but listings return 403 (a 1.3 KB origin error, not the
  Cloudflare page).
- Courtesy delay between requests: 0.4 s.

### Which years have XML

| Election | Base URL | Contents |
|---|---|---|
| 2026 | `https://www.electionresults.govt.nz/electionresults_2026_preliminary/xml/` | preliminary count. The live feed was at `https://electionresults.govt.nz/xml/` on 8 November 2026 and has since moved. |
| 2023 | `https://www.electionresults.govt.nz/electionresults_2023/xml/` | official results (`updated="2024-11-10"`) |
| 2020 | `https://www.electionresults.govt.nz/electionresults_2020/xml/` | official results (`updated="2020-11-20"`) |
| 2017 | `https://www.electionresults.govt.nz/electionresults_2017/xml/` | official results (`updated="2017-10-07"`), 71 electorates, same layout (checked 10 November 2026) |
| 2014, 2011, 2008 | none: `electionresults_YYYY/xml/election.xml` gives a 404 | CSVs only, which are blocked |

No 2023 preliminary feed found: `electionresults_2023_preliminary` gives a 404
on both hosts. The 2023 preliminary count was recovered from the Wayback
Machine instead (next section).

### 2023 preliminary count from the Wayback Machine (checked 10 November 2026)

- The Wayback Machine has the HTML page for each electorate,
  `electionresults_2023_preliminary/electorate-details-NN.html`, for 71 of 72
  electorates, captured 27 October – 1 November 2023, all showing 100% of
  results counted. **No. 39 (Port Waikato) wasn't archived**, although the page
  existed (`electorate-status.html` links to it). A candidate died, so the
  electorate vote went to a by-election, but the party vote was counted as
  normal: the status page shows 100% of its voting places counted, with no
  candidates. There are no archived XML, CSVs or spreadsheets. The only other
  captures are summary pages and `statistics/pdf/61_ElectionDay.pdf`.
- **National preliminary party totals** are on the archived overview page
  (`index.html`, captured 20231026013849, 100% of results counted): valid party
  votes for each party, 2,254,441 in total (National 878,288, Labour 606,663,
  Green 242,845, ACT 202,664, NZ First 145,649, Te Pāti Māori 58,949). Not yet
  scraped by any script. Subtracting the 71 electorates' sums (2,221,193) gives
  **Port Waikato's preliminary party votes: 33,248 valid**, against 42,399 in
  the official count (ratio 1.28, inside the other electorates' range). Every
  party's implied figure is positive, and the six largest parties' ratios are
  1.24–1.70 (National 16,885 → 21,277). Port Waikato's preliminary party
  informals can't be recovered this way, because the overview page has no
  informals figure.
- The pages give electorate totals only: candidate votes, party votes,
  candidate and party informals, and a total for each side. They don't say
  which party a candidate belongs to, and they use parties' full names
  (`party_name` in `parties.xml`, which for the Animal Justice Party has a
  trailing space).
- **Rate limit:** at 1 request a second the Wayback Machine refused all
  connections from our IP address after 17 pages, for a few minutes. 5 seconds
  between requests worked.
- `https://web.archive.org/web/<timestamp>id_/<url>` serves the page as
  originally captured, without the Wayback toolbar, but still gzip-compressed.
- Checked against the 2023 official feed: all 71 electorate names, every party
  and every candidate match, and every candidate's party (taken from the
  official `candidates.xml`) matches. Final votes cast are 1.14 (Invercargill)
  to 1.54 (Māngere) times the preliminary votes cast. In 24 party rows (all
  very small parties, the largest drop being 56 votes) and 1 candidate row,
  the final count is lower than the preliminary count.

### XML layout (the same for 2017, 2020, 2023 and 2026)

- Top level: `election.xml`, `electorates.xml`, `parties.xml`,
  `candidates.xml`, `statistics.xml`, `votingplaces.xml`.
  - `election.xml`: national statistics and party totals and seats.
    `total_special_votes` and `total_minimal_votes` are national figures only.
    In official results (2023) `total_special_votes` is 0.
  - `electorates.xml`: `e_no` → electorate name.
  - `parties.xml`: `p_no` → abbreviation, short name, full name, whether
    registered.
  - `candidates.xml`: `c_no` → name, electorate, party, list number. **Party
    `0` means independent and isn't listed in `parties.xml`.** Electorate `0`
    means list-only.
  - `votingplaces.xml`: `vp_id`, `vp_e_no` (the place's home electorate),
    address, lat/lon. It has **no** `vp_no` and doesn't say which electorates'
    votes a place took, so voting-place file names can't be built from it. Use
    the directory listings.
- `eNN/eNN.xml` (two-digit electorate number): electorate statistics (votes
  cast, party informals, candidate informals, etc.), plus party and candidate
  votes keyed by `p_no` / `c_no`. Attributes include `final` and `updated`.
- `eNN/votingplaces/NN-VVPPP.xml`: one file per voting place per electorate
  whose votes it took. `NN` = the electorate, `VV` = the voting place's home
  electorate, `PPP` = `vp_no`. For example, `01-47017` is a place in electorate
  47 that took Auckland Central votes. Contains ballot papers issued,
  informals, and party and candidate votes. `vp_no` 200+ and `vp_no` 0 entries
  exist (e.g. `01-23000`, with 0 ballots issued); what they mean is unknown.
  Numbering has gaps.

### Deriving per-electorate special votes

- **Decision (10 November 2026): don't derive special votes by subtracting
  voting-place sums from `eNN.xml`.** Whether voting-place files include
  specials isn't consistent between years (below), and even for 2023 the
  exclusion is inferred, not confirmed against a published figure. Use
  recovered preliminary counts and the preliminary-to-final gap instead.
- **Whether voting-place files include specials depends on the year**
  (spot-checked 10 November 2026 by comparing `eNN.xml` with the sum of that
  electorate's voting-place files, for every party, candidate and informal
  count):
  - **2023 official: apparently ordinary votes only (inferred).** Every party
    and candidate has more votes in `eNN.xml` than in the voting-place sum
    (never fewer), and so do informals. Gaps: Christchurch Central 9,927 party / 9,122 candidate (24.6%
    of votes cast), Palmerston North 6,072 / 5,524 (16.7%), Wellington Central
    13,150 / 12,544 (28.3%), Tāmaki Makaurau 8,512 / 7,048 (31.8%).
  - **2020 and 2017 official: specials already included.** Sums nearly or
    exactly equal `eNN.xml`, informals included: 2020 Dunedin gap 18 party / 13
    candidate, 2020 Northland 60 / 60, 2017 Rongotai 0 / 0. The files are dated
    after the official results (2020-11-20, 2017-10-07), so this isn't a
    preliminary snapshot. Which files hold the specials is unknown: no tag
    marks them. Most votes are in `vp_no` 200+ files (e.g. 33,457 of 46,103
    ballots in Dunedin 2020), so they may be folded into those. The small 2020
    gaps aren't explained.
  - **2026 preliminary: sums equal `eNN.xml` exactly** (Auckland Central,
    Glendene, Palmerston North, Southland, Te Tai Tokerau). That's expected,
    since specials aren't counted yet. Ballot papers issued can differ slightly
    from `total_votes_cast` (e.g. 30,161 vs 30,110 in Auckland Central).
  - `vp_no` 0 and 200+ files don't hold the 2023 specials: they contain
    ordinary votes (e.g. 7,583 ballots in Wellington Central's 200+ files) and
    the gap remains with them included.
- For reference only (not to be relied on): in 2023, `eNN.xml` totals − the
  sum of voting-place files gives what look like specials. For Auckland
  Central (61 files): 35,463 votes cast vs 23,488 ballot papers issued at
  voting places; a gap of 12,046 party votes and 11,227 candidate votes. This
  rests on an inference: the gaps are always positive, 17–32% of votes cast,
  and largest in seats expected to have many specials. Missing voting-place
  files would also produce positive gaps.
- The preliminary-to-final gap also includes official-count revisions to
  ordinary votes, not just specials, so recovered preliminary counts (from the
  Wayback Machine) are the more direct source anyway. The 2023 subtraction
  figures are at most a rough sanity check on them.
- The XML gives **one** special-vote total. Unlike the CSVs it doesn't split
  specials into overseas, before polling day, on polling day and party-only
  (see `SPECIAL_ROW_NAMES` in `electorate.py` in
  [czlee/elections-2020](https://github.com/czlee/elections-2020)).
- Size: 2023 has about 10,655 voting-place results (`total_voting_places_counted`),
  about 72 minutes at 0.4 s per request. 2026 preliminary has 9,389.

### Quirks in the 2026 preliminary data (8 November 2026 snapshot)

- In every electorate, exactly one of (party valid + party informals) and
  (candidate valid + candidate informals) equals `total_votes_cast`, and the
  other is short by up to 401 votes (4,279 in total). This is probably ballots
  with one half left blank. So `total_votes_cast` = the larger of the two.
- The electorates' `total_votes_cast` values sum to 2,433,679, but
  `election.xml` says 2,432,403 (a difference of 1,276). Not explained.
- Party votes summed over electorates match `election.xml`'s party totals
  exactly.

### Electorates

- 2023: 72 electorates. 2026: 71 electorates, some renamed or new (e.g.
  Glendene is electorate 11 in 2026). No 2023 → 2026 correspondence table has
  been looked for yet.

## Code status

- `download.py`: downloads the top-level and `eNN/eNN.xml` files for one
  feed into `<outdir>/raw/` and writes `candidate_votes.csv`,
  `party_votes.csv`, `electorate_stats.csv` and `national_stats.csv`. Pick a
  feed with `--election` (`2026-prelim` (default), `2023`, `2020`, `2017`) or
  `--base URL`; the output defaults to `results/<election>`. It doesn't fetch
  voting-place files. Checked 10 November 2026: it runs for 2017, 2020 and 2023,
  and party votes summed over electorates match `election.xml` for each.
- `scrape_wayback_prelim.py`: scrapes the 2023 preliminary count from the
  Wayback Machine into `results/2023-prelim/`, writing `candidate_votes.csv` and
  `party_votes.csv` with the same columns and names as `download.py --election
  2023`, and an `electorate_stats.csv` with different columns (the capture's
  timestamp, results counted, and both totals; `total_votes_cast` is the
  larger of the two). It reports any electorate whose sums don't match its
  totals, any partial count, and any candidate or party missing from the
  official feed.
- The original CSV-based code (1999 onwards: `download.py`, `electorate.py`,
  `analyse.py`, `config.py`) is in
  [czlee/elections-2020](https://github.com/czlee/elections-2020) (locally
  `~/elections-2020`). It can't currently be run because the CSVs are blocked.
  It's kept there in case the CSVs become reachable again, since the CSVs are
  the only source for pre-2017 elections and for the breakdown of special votes
  by category.
- Moved to this repo on 10 November 2026. The `results/` data (2023, 2023-prelim,
  2026-prelim) was copied over too; it's gitignored.

## Plans

None yet. This section will hold the plan for the 2026 special-votes
projection and any refactoring.
