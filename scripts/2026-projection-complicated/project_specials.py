"""Projects the 2026 final party vote by applying a past election's special
votes to the 2026 preliminary count. National level only. The past election
(the "base") is 2023 by default; 2017 and 2020 also work (--base).

"Special votes" here means final minus preliminary valid party votes. That's
mostly the special votes, but it also includes changes to ordinary votes in the
official count; we use the term for the difference throughout. It's split into
three pools, which are projected separately:

  overseas   overseas special votes, as counted in the base election
             (download_specials.py)
  domestic   all other special votes, as counted
  revisions  the rest: final minus preliminary ordinary votes, i.e. the
             official count's corrections to the preliminary count. These are
             lumpy (a few electorates change by several percent, most barely
             at all), so their party mix isn't projected: they're shared out
             like the preliminary count.

  1. For each party, the base multipliers are its share of the base
     election's overseas special votes, and of its domestic special votes,
     each divided by its share of the base's ordinary votes in the final
     count. (Not the preliminary count: that would mix the revisions into
     the multipliers.) Every party's revisions multiplier is 1.
  2. In each pool, the projected 2026 share is the 2026 preliminary share
     times the multiplier, normalised to add to 100%. Revisions are shared
     like the preliminary count, so the 2026 final count's ordinary votes
     are shared like it too, and the preliminary share stands in for the
     ordinary-vote share that the multipliers were measured against.
  3. The number of 2026 votes in each pool:
       overseas   the Electoral Commission's 2026 estimate of overseas (and
                  dictation) votes, times the base election's overseas
                  special votes divided by its overseas estimate
       domestic   the same, with the rest of each estimate and the domestic
                  special votes
       revisions  the 2026 preliminary count, times the base's revisions
                  divided by its preliminary count
  4. The projected final count is the preliminary count plus the projected
     votes in all three pools.
  5. Seats are allocated (seats.py) from both the preliminary and the
     projected party votes. Electorate seats are the preliminary count's
     winners in both: the projection doesn't change electorates.

The press releases' overseas estimates include dictation votes, which are
counted as domestic, so the overseas adjustment (step 3) is a little under 1
and the domestic one a little over. That's fine as long as dictation votes are
a similar share in the base election and 2026.

Parties are linked between years by party_id in party_names.toml (see
parties.py). A 2026 party that was part of an umbrella party in the base
election uses the umbrella party's multiplier. A 2026 party with no
counterpart in the base election gets a multiplier of 1.

Inputs: results/<base>/party_votes.csv (download.py --election <base>),
results/<base>/party_votes_by_category.csv (download_specials.py --election
<base>), results/2026-prelim/party_votes.csv (download.py), and the base election's
preliminary count: for 2020 and 2023 the overview page saved from the Wayback
Machine, for 2017 results/2017-prelim/party_votes.csv
(scrape_wayback_prelim.py --election 2017), which sums exactly to 2017's
overview page (see NOTES.md).
"""
import argparse
import csv
import html
import os
import re
import sys
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # shared modules are in scripts/
from parties import PartyNames
from seats import TOTAL_SEATS, allocate

# Special-vote estimates from the preliminary-results press releases (see NOTES.md).
# The overseas estimates include dictation votes.
SPECIAL_ESTIMATE_2023 = 567000
SPECIAL_ESTIMATE_2026 = 399365
SPECIAL_ESTIMATE_OVERSEAS_2026 = 96947
POOLS = ["overseas", "domestic", "revisions"]

PRELIM_2023_OVERVIEW = "results/2023-prelim/raw/index-20231026013849.html"
FINAL_2023_PARTY_VOTES = "results/2023/party_votes.csv"
PRELIM_2026_PARTY_VOTES = "results/2026-prelim/party_votes.csv"
PRELIM_2026_CANDIDATE_VOTES = "results/2026-prelim/candidate_votes.csv"

# Base elections. "prelim" is ("overview", saved overview page) or ("csv",
# electorate-level party_votes.csv); "estimate" and "overseas_estimate" are the
# press release's special-vote estimates (see NOTES.md); "categories" is the
# official count split into ordinary, overseas and domestic special votes.
BASES = {
    "2017": {"estimate": 384072, "overseas_estimate": 61375,
             "prelim": ("csv", "results/2017-prelim/party_votes.csv"),
             "final": "results/2017/party_votes.csv",
             "categories": "results/2017/party_votes_by_category.csv"},
    "2020": {"estimate": 480000, "overseas_estimate": 66000,
             "prelim": ("overview", "results/2020-prelim/raw/index-20201103192629.html"),
             "final": "results/2020/party_votes.csv",
             "categories": "results/2020/party_votes_by_category.csv"},
    "2023": {"estimate": SPECIAL_ESTIMATE_2023, "overseas_estimate": 80000,
             "prelim": ("overview", PRELIM_2023_OVERVIEW),
             "final": FINAL_2023_PARTY_VOTES,
             "categories": "results/2023/party_votes_by_category.csv"},
}
DEFAULT_BASE = "2023"


def default_output(base):
    if base == DEFAULT_BASE:
        return "results/projection-2026-complicated/national.csv"
    return "results/projection-2026-complicated/national-base{0}.csv".format(base)


def read_party_totals(filename):
    """Sums an electorate-level party_votes.csv to national totals."""
    totals = Counter()
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            totals[row["party"]] += int(row["votes"])
    return totals


def read_overview(filename):
    """Reads national party totals from a preliminary overview page (2020 and
    2023 share a layout). Rows with "-" (2023: Freedoms NZ's component
    parties) are skipped. Checks the parties against the page's total row."""
    with open(filename, encoding="utf-8") as f:
        text = f.read()
    table = text[text.index('id="overall-results-table"'):]
    table = table[:table.index("</table>")]
    totals = Counter()
    page_total = None
    for row in re.findall(r"<tr.*?</tr>", table, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) < 2 or cells[1] == "-":
            continue
        votes = int(cells[1].replace(",", ""))
        if cells[0] == "Total":
            page_total = votes
        else:
            totals[cells[0]] += votes
    if page_total != sum(totals.values()):
        raise ValueError("overview parties sum to {0}, but its total is {1}".format(
            sum(totals.values()), page_total))
    return totals


def electorate_winners(filename, election, names, parties):
    """Counts electorates won from a candidate_votes.csv. Returns ({party_id:
    electorates}, electorates won by candidates not from any of `parties`,
    e.g. independents). Raises an error on a tie for first."""
    best = {}
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            votes = int(row["votes"])
            current = best.get(row["elec_id"])
            if current is None or votes > current[0]:
                best[row["elec_id"]] = (votes, [row["party"]])
            elif votes == current[0]:
                current[1].append(row["party"])
    won = Counter()
    other = 0
    for elec_id, (votes, winners) in best.items():
        if len(winners) > 1:
            raise ValueError("electorate {0}: tie for first between {1}".format(elec_id, winners))
        name = winners[0]
        party_id = names.ids.get((election, name))
        if party_id in parties:
            won[party_id] += 1
        else:
            other += 1  # independent, or a party with no party votes (no list)
    return won, other


def shares(totals):
    total = sum(totals.values())
    return {party: votes / total for party, votes in totals.items()}


def read_base_prelim(base):
    kind, filename = BASES[base]["prelim"]
    return read_overview(filename) if kind == "overview" else read_party_totals(filename)


def read_categories(filename):
    """Sums party_votes_by_category.csv (download_specials.py) to national
    totals: {category: Counter({party: votes})}."""
    totals = {}
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            totals.setdefault(row["category"], Counter())[row["party"]] += int(row["votes"])
    return totals


def project_pool(prelim_share, multipliers, volume):
    """Shares out `volume` votes in proportion to prelim_share * multiplier.
    Returns ({party: share of the pool}, {party: votes})."""
    unnormalised = {p: prelim_share[p] * multipliers[p] for p in prelim_share}
    norm = sum(unnormalised.values())
    share = {p: u / norm for p, u in unnormalised.items()}
    return share, {p: s * volume for p, s in share.items()}


def compute(base=DEFAULT_BASE):
    """Runs the projection from the base election `base`. Returns a dict of
    its inputs and intermediates: base totals, `pools` ({pool: details, see
    below}), 2026 shares, projected special and final votes ({party_id:
    value}), and seats ({party_id: (electorate, list, total)}) for the
    preliminary and projected party votes.

    Each pool's details are its base votes (`base_total`, and `base`
    {party_id: votes} for overseas and domestic), `multipliers_base`,
    `multipliers` (2026 parties), `adjustment` (the step 3 ratio), `volume`,
    `share` and `specials` (2026 parties).

    For anything that expects a single pool, the result also has blended
    figures: `multipliers_base` and `special_share_base` from the base's
    final minus preliminary votes, as before the split; `multipliers`, the
    effective 2026 multipliers (projected special share / preliminary share);
    and `adjustment`, the projected special votes / the 2026 estimate."""
    names = PartyNames()
    estimate_base = BASES[base]["estimate"]
    overseas_estimate_base = BASES[base]["overseas_estimate"]
    prelim_base = names.to_ids(base, read_base_prelim(base))
    final_base = names.to_ids(base, read_party_totals(BASES[base]["final"]))
    categories = {c: names.to_ids(base, v) for c, v in read_categories(BASES[base]["categories"]).items()}
    prelim_2026_by_name = read_party_totals(PRELIM_2026_PARTY_VOTES)
    prelim_2026 = names.to_ids("2026", prelim_2026_by_name)
    display_names = {names.party_id("2026", name): name for name in prelim_2026_by_name}

    unmatched = set(prelim_base) ^ set(final_base)
    if unmatched:
        raise ValueError("{0} preliminary and final parties don't match: {1}".format(base, sorted(unmatched)))
    category_total = sum(sum(v.values()) for v in categories.values())
    if category_total != sum(final_base.values()):
        raise ValueError("{0}: categories add up to {1}, final count is {2}".format(
            base, category_total, sum(final_base.values())))

    # Blended base figures (final minus preliminary), for single-pool consumers
    specials_base = Counter({p: final_base[p] - prelim_base[p] for p in final_base})
    prelim_share_base = shares(prelim_base)
    special_share_base = shares(specials_base)
    multipliers_base = {p: special_share_base[p] / prelim_share_base[p] for p in final_base}

    # Steps 1 and 3: base multipliers and volumes for each pool
    prelim_share_2026 = shares(prelim_2026)
    links = {p: names.counterpart(p, base, final_base) for p in prelim_2026}
    ordinary_base = Counter({p: categories["ordinary"].get(p, 0) for p in final_base})
    ordinary_share_base = shares(ordinary_base)
    pools = {}
    for pool, estimate_2026, estimate in [
            ("overseas", SPECIAL_ESTIMATE_OVERSEAS_2026, overseas_estimate_base),
            ("domestic", SPECIAL_ESTIMATE_2026 - SPECIAL_ESTIMATE_OVERSEAS_2026,
             estimate_base - overseas_estimate_base)]:
        votes = Counter({p: categories[pool].get(p, 0) for p in final_base})
        pool_share = shares(votes)
        m_base = {p: pool_share[p] / ordinary_share_base[p] for p in final_base}
        base_total = sum(votes.values())
        pools[pool] = {"base": votes, "base_total": base_total, "multipliers_base": m_base,
                       "estimate_base": estimate, "estimate_2026": estimate_2026,
                       "adjustment": base_total / estimate, "volume": estimate_2026 * base_total / estimate}
    revisions_base = sum(specials_base.values()) - pools["overseas"]["base_total"] - pools["domestic"]["base_total"]
    ratio = revisions_base / sum(prelim_base.values())
    pools["revisions"] = {"base_total": revisions_base, "multipliers_base": {p: 1.0 for p in final_base},
                          "adjustment": ratio, "volume": sum(prelim_2026.values()) * ratio}

    # Step 2: projected 2026 shares in each pool
    for pool in pools.values():
        pool["multipliers"] = {p: pool["multipliers_base"][links[p]] if links[p] else 1.0 for p in prelim_2026}
        pool["share"], pool["specials"] = project_pool(prelim_share_2026, pool["multipliers"], pool["volume"])

    # Step 4: projected final count
    specials_2026 = {p: sum(pool["specials"][p] for pool in pools.values()) for p in prelim_2026}
    projected_specials_total = sum(specials_2026.values())
    special_share_2026 = {p: v / projected_specials_total for p, v in specials_2026.items()}
    multipliers = {p: special_share_2026[p] / prelim_share_2026[p] for p in prelim_2026}
    adjustment = projected_specials_total / SPECIAL_ESTIMATE_2026
    final_2026 = {p: prelim_2026[p] + specials_2026[p] for p in prelim_2026}

    # Step 5: seats
    electorates, other_electorates = electorate_winners(PRELIM_2026_CANDIDATE_VOTES, "2026", names, prelim_2026)
    prelim_seats = allocate(prelim_2026, electorates, other_electorates)
    final_seats = allocate(final_2026, electorates, other_electorates)

    return {
        "base": base, "names": names, "display_names": display_names,
        "prelim_base": prelim_base, "final_base": final_base, "specials_base": specials_base,
        "prelim_share_base": prelim_share_base, "special_share_base": special_share_base,
        "multipliers_base": multipliers_base, "adjustment": adjustment, "pools": pools,
        "ordinary_base": ordinary_base,
        "estimate_base": estimate_base, "estimate_2026": SPECIAL_ESTIMATE_2026,
        "projected_specials_total": projected_specials_total,
        "prelim_2026": prelim_2026, "prelim_share_2026": prelim_share_2026, "links": links,
        "multipliers": multipliers, "special_share_2026": special_share_2026,
        "specials_2026": specials_2026, "final_2026": final_2026,
        "electorates": electorates, "other_electorates": other_electorates,
        "prelim_seats": prelim_seats, "final_seats": final_seats,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", choices=sorted(BASES), default=DEFAULT_BASE,
                        help="past election whose special votes to apply (default %(default)s)")
    parser.add_argument("--output", help="default results/projection-2026-complicated/national.csv for 2023, "
                        "national-base<year>.csv otherwise")
    args = parser.parse_args()
    base = args.base
    args.output = args.output or default_output(base)

    c = compute(base)
    names, links, prelim_2026 = c["names"], c["links"], c["prelim_2026"]
    prelim_seats, final_seats = c["prelim_seats"], c["final_seats"]
    other_electorates, display_names = c["other_electorates"], c["display_names"]
    final_total = sum(c["final_2026"].values())
    pools = c["pools"]

    rows = []
    parties = sorted(prelim_2026, key=lambda p: -prelim_2026[p])
    for party in parties:
        rows.append([names.short_names[party], links[party] or "", prelim_2026[party],
                     100 * c["prelim_share_2026"][party], c["multipliers"][party],
                     100 * c["special_share_2026"][party], c["specials_2026"][party], c["final_2026"][party],
                     100 * c["final_2026"][party] / final_total,
                     prelim_seats[party][2], final_seats[party][0], final_seats[party][1], final_seats[party][2],
                     pools["overseas"]["multipliers"][party], pools["domestic"]["multipliers"][party]]
                    + [pools[pool]["specials"][party] for pool in POOLS])

    print("{0}: preliminary {1:,}, final {2:,}, special votes {3:,}, estimate {4:,} (overseas {5:,})".format(
        base, sum(c["prelim_base"].values()), sum(c["final_base"].values()), sum(c["specials_base"].values()),
        c["estimate_base"], BASES[base]["overseas_estimate"]))
    for pool in ["overseas", "domestic"]:
        p = pools[pool]
        print("  {0:<9} {1:>8,} / estimate {2:>7,} = {3:.4f}; 2026 estimate {4:>7,} -> {5:>8,.0f}".format(
            pool, p["base_total"], p["estimate_base"], p["adjustment"], p["estimate_2026"], p["volume"]))
    p = pools["revisions"]
    print("  {0:<9} {1:>8,} / preliminary = {2:.4f}; 2026 preliminary {3:,} -> {4:,.0f}".format(
        "revisions", p["base_total"], p["adjustment"], sum(prelim_2026.values()), p["volume"]))
    print("2026: preliminary {0:,}, estimate {1:,}, projected special votes {2:,.0f}, projected final {3:,.0f}".format(
        sum(prelim_2026.values()), SPECIAL_ESTIMATE_2026, c["projected_specials_total"], final_total))
    print()
    print("{0:<20} {1:>9} {2:>7} {3:>6} {4:>6} {5:>6} {6:>7} {7:>8} {8:>9} {9:>7}  {10:>6} {11:>4} {12:>4} {13:>5}".format(
        "party", "prelim", "prel%", "m_ovs", "m_dom", "mult", "spec%", "specials", "final", "final%",
        "prelim", "elec", "list", "final"))
    print(" " * 89 + "seats:")
    for r in rows:
        print("{0:<20} {2:>9,} {3:>7.2f} {13:>6.3f} {14:>6.3f} {4:>6.3f} {5:>7.2f} {6:>8,.0f} {7:>9,.0f} {8:>7.2f}  "
              "{9:>6} {10:>4} {11:>4} {12:>5}".format(*r))
    print("{0:<20} {1:>80} {2:>4} {3:>4} {4:>5}".format(
        "total", sum(r[9] for r in rows), sum(r[10] for r in rows), sum(r[11] for r in rows),
        sum(r[12] for r in rows)))
    if other_electorates:
        print("plus {0} electorate(s) won by independents or parties without a list".format(other_electorates))
    for label, seats in [("preliminary", prelim_seats), ("projected", final_seats)]:
        house = sum(s[2] for s in seats.values()) + other_electorates
        print("{0}: {1} seats, overhang {2}, majority {3}".format(label, house, house - TOTAL_SEATS, house // 2 + 1))
    no_link = [r[0] for r in rows if not r[1]]
    print()
    print("multiplier 1 (no {0} counterpart): ".format(base) + ", ".join(no_link))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["party_id", "short_name", "name", "party_id_" + base, "prelim_votes", "prelim_pct", "multiplier",
                         "projected_special_pct", "projected_special_votes", "projected_final_votes",
                         "projected_final_pct", "prelim_seats", "projected_electorate_seats",
                         "projected_list_seats", "projected_seats", "multiplier_overseas", "multiplier_domestic",
                         "projected_overseas_votes", "projected_domestic_votes", "projected_revision_votes"])
        for party, r in zip(parties, rows):
            writer.writerow([party, r[0], display_names[party]] + r[1:3] + ["{0:.4f}".format(r[3]), "{0:.4f}".format(r[4]), "{0:.4f}".format(r[5]),
                                     "{0:.0f}".format(r[6]), "{0:.0f}".format(r[7]), "{0:.4f}".format(r[8])] + r[9:13]
                             + ["{0:.4f}".format(m) for m in r[13:15]] + ["{0:.0f}".format(v) for v in r[15:]])
    print("wrote {0} ({1} rows)".format(args.output, len(rows)))


if __name__ == "__main__":
    main()
