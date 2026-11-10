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

### 2017 and 2020 preliminary counts from the Wayback Machine (checked 10 November 2026)

- **2017: complete.** All 71 `electionresults_2017_preliminary/electorate-details-NN.html`
  pages are archived (captured 30 September – 12 October 2017, all at 100% of
  results counted), in the same layout as 2023, so the same parser works. Many
  captures are under `http://...:80/` URLs; the CDX index finds them anyway.
  Checks: candidate and party votes plus informals equal the page totals in
  every electorate; every electorate name, party and candidate (and every
  candidate's party) matches the 2017 official feed; and the 71 electorates'
  valid party votes sum to **2,169,802, exactly the national preliminary total**
  on the archived overview page (`index.html`, captured 20171011234809), with
  National, Labour, Green, NZ First and ACT also matching exactly. Final votes
  cast are 1.11 (Invercargill) to 1.39 (Auckland Central) times the preliminary
  votes cast. In 27 party rows (all small parties; the largest drop is the Māori
  Party in electorate 20, 195 → 92) and 2 candidate rows, the final count is lower.
- 2017 also has 71 archived `statistics/csv/NN_ElectionDay.csv` files. Not
  looked at yet; they may give the preliminary count by voting place.
- **2020: electorate pages unusable.** All 72 electorate pages were captured
  (178 captures, 18 October 2020 into 2021), but every capture is a 403 (162,
  about 5–7 KB, i.e. the Cloudflare block page, which shows as a CAPTCHA) or a
  404 (16). Captures of `electionresults_2020/electorate-details-*` from before
  the official results (17 October – 6 November 2020) are all 403 too. The only
  good 2020 preliminary pages are `index.html` (captured 20201103192629) and
  `referendums-results.html`. `index.html` has the **national preliminary party
  votes** at 100% counted: 2,383,796 valid party votes (Labour 1,171,544,
  National 638,606, ACT 190,139, Green 180,347, NZ First 63,534, Māori Party
  23,932). Other archives (e.g. archive.today) haven't been checked.
- **2014 and earlier:** nothing archived under `electionresults_2014_preliminary/`,
  and there's no official XML to match against.

### Special-vote estimates in the preliminary press releases (checked 10 November 2026)

- **2026** ([release](https://elections.nz/media-and-news/2026/2026-general-election-preliminary-results),
  fetchable with curl): "The number of special votes is approximately
  399,365 including 96,947 overseas and dictation votes", on 2,432,403
  ordinary votes counted (including informals). **The XML's
  `total_special_votes` (297,418) is different**: 101,947 lower, which is the
  overseas and dictation votes plus exactly 5,000. Not explained. Use the press
  release figure.
- **2023** ([release](https://elections.nz/media-and-news/2023/election-night-results-for-the-2023-general-election),
  blocked by Incapsula, so read via Wayback capture `20231021094025`): "Special
  declaration votes still to be counted are estimated at 567,000 (20.2% of
  total votes). This includes an estimated 80,000 overseas and dictation
  votes." Its party table (2,244,380 total, National 875,234) was written on
  election night, before counting finished, so it's slightly lower than the
  100%-counted overview page below. Use the overview page.
  - Every party is 0.2–1.0% higher on the overview page than in the release
    (total +10,061, ratio 1.0045; Te Pāti Māori +1.0%, Labour +0.6%). So it's
    a later snapshot, not a different definition: both are valid party votes.
    The release's "2,244,380 ordinary votes counted" is that same valid party
    total, though the release calls it ordinary votes. Captures of the overview
    page on 25 October (`20231025055838`) and 26 October 2023 are identical
    (100.0% counted).
  - So don't mix the two: a ratio like (site valid party votes / release
    total) comes out above 1. In 2026 the release and the feed agree (party
    total 2,418,565; 2,432,403 votes counted including informals).

### 2023 preliminary national party totals (checked 10 November 2026)

- Saved from Wayback capture `20231026013849` of
  `electionresults_2023_preliminary/index.html` to
  `results/2023-prelim/raw/index-20231026013849.html` (table
  `#overall-results-table`). Not yet parsed by any script. Total 2,254,441.
- The overview uses some names that differ from the official feed's
  `party_votes.csv`: "New Zealand Loyal" (official: "NZ Loyal") and "Leighton
  Baker Party" (official: "Leighton Baker"). It lists Freedoms NZ's component
  parties (NZ Outdoors & Freedom, Rock the Vote NZ, Vision New Zealand) with
  "-", since votes for them counted under Freedoms NZ.
- **`p_no` isn't stable across elections**, so it can't be used to link
  parties between 2023 and 2026. Most numbers carry over (e.g. 24: "The
  Opportunities Party (TOP)" → "Opportunity Party", 34: "New Conservatives" →
  "Conservative Party NZ", 52: "Animal Justice Party" → "Animal Justice Party
  Aotearoa New Zealand"), but New Zealand Loyal (54 → 70), Vision New Zealand
  (32 → 66) and the Alliance (6 → 68) got new numbers.

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
- `scrape_wayback_prelim.py`: scrapes the 2023 or 2017 preliminary count
  (`--election`, default 2023) from the Wayback Machine into
  `results/<election>-prelim/`, writing `candidate_votes.csv` and
  `party_votes.csv` with the same columns and names as `download.py --election
  <election>`, and an `electorate_stats.csv` with different columns (the capture's
  timestamp, results counted, and both totals; `total_votes_cast` is the
  larger of the two). It reports any electorate whose sums don't match its
  totals, any partial count, and any candidate or party missing from the
  official feed. It doesn't scrape the national totals on `index.html`.
  Checked 10 November 2026: it runs for 2023 and 2017 with no problems
  reported except 2023's missing Port Waikato page.
- `project_specials.py` (10 November 2026): national projection of the 2026
  final party vote from 2023's preliminary-to-final changes; method in its
  docstring. Writes `results/projection-2026/national.csv`. Reads the 2023
  preliminary totals straight from the saved overview page. Parties new in 2026
  get a multiplier of 1.
- `seats.py` (10 November 2026): MMP seat allocation (5% or one electorate;
  Sainte-Laguë over 120 less independents' electorates; overhang enlarges the
  House; raises an error on a tie for the last seat). `python3 seats.py` checks it against
  `election.xml`: matches 2017 (120), 2023 (122, Te Pāti Māori overhang 2) and
  2026 preliminary (131, overhang 11). 2023's `total_electorates_final` is 72
  but `candidate_seats` sum to 71: Port Waikato's by-election came after
  allocation, so don't read the gap as an independent. `project_specials.py`
  allocates seats for both the preliminary and projected party votes, with
  electorates held at the preliminary winners.
- `party_names.toml` + `parties.py`: links parties across elections.
  One table per stable `party_id`, giving the name(s) it appears under in each
  election's data (TOML rather than CSV for readability, decided with the user
  on 10 November 2026; `tomllib` is in the standard library), and `part_of`
  for component parties of an umbrella party (2023: Vision New
  Zealand, NZ Outdoors & Freedom and Rock the Vote NZ were part of Freedoms NZ).
  Every name must be listed, so a new election fails loudly until its parties
  are added. Covers 2017, 2023 and 2026 (all datasets in `results/`). Decided
  with the user: NZ Loyal (re-registered) is the same party in 2023 and 2026;
  2026 Vision New Zealand and NZ Outdoors & Freedom compare against Freedoms NZ
  in 2023. My own calls, not yet reviewed: Māori Party (2017) = Te Pāti Māori;
  Conservative (2017) = New Conservatives = Conservative Party NZ; NZ Outdoors
  Party (2017) = NZ Outdoors & Freedom Party; the 2026 Alliance Party isn't
  linked to anything, since the Alliance didn't stand in 2017 or 2023. The 2023 adjustment comes out
  at 1.0525 (596,770 valid party votes from specials vs the 567,000 estimate),
  so it scales the 2026 estimate *up*, to about 420,333.
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
