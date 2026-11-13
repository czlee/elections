"""Projects the 2026 final party vote by applying 2023's special votes to the
2026 preliminary count. National level only.

"Special votes" here means final minus preliminary valid party votes. That's
mostly the special votes, but it also includes changes to ordinary votes in the
official count; we use the term for the difference throughout.

  1. For each party, the 2023 multiplier is its share of the special votes
     divided by its share of the preliminary count.
  2. The projected 2026 share of special votes is the 2026 preliminary share
     times the multiplier, normalised to add to 100%.
  3. The number of 2026 special votes is the Electoral Commission's estimate
     times an adjustment: 2023 special votes (valid party votes) divided by
     the 2023 estimate.
  4. The projected final count is the preliminary count plus the projected
     special votes.
  5. Seats are allocated (seats.py) from both the preliminary and the
     projected party votes. Electorate seats are the preliminary count's
     winners in both: the projection doesn't change electorates.

Parties are linked between years by party_id in party_names.toml (see
parties.py). A 2026 party that was part of an umbrella party in 2023 uses the
umbrella party's multiplier. A 2026 party with no 2023 counterpart gets a
multiplier of 1.

Inputs: results/2023/party_votes.csv (download.py --election 2023),
results/2026-prelim/party_votes.csv (download.py), and the 2023 preliminary
overview page saved from the Wayback Machine (see NOTES.md).
"""
import argparse
import csv
import html
import os
import re
from collections import Counter

from parties import PartyNames
from seats import TOTAL_SEATS, allocate

# Special-vote estimates from the preliminary-results press releases (see NOTES.md).
SPECIAL_ESTIMATE_2023 = 567000
SPECIAL_ESTIMATE_2026 = 399365

PRELIM_2023_OVERVIEW = "results/2023-prelim/raw/index-20231026013849.html"
FINAL_2023_PARTY_VOTES = "results/2023/party_votes.csv"
PRELIM_2026_PARTY_VOTES = "results/2026-prelim/party_votes.csv"
PRELIM_2026_CANDIDATE_VOTES = "results/2026-prelim/candidate_votes.csv"


def read_party_totals(filename):
    """Sums an electorate-level party_votes.csv to national totals."""
    totals = Counter()
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            totals[row["party"]] += int(row["votes"])
    return totals


def read_overview(filename):
    """Reads national party totals from the 2023 preliminary overview page.
    Rows with "-" (Freedoms NZ's component parties) are skipped. Checks the
    parties against the page's total row."""
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


def compute():
    """Runs the projection. Returns a dict of its inputs and intermediates:
    2023 totals, multipliers, the adjustment, 2026 shares, projected special
    and final votes ({party_id: value}), and seats ({party_id: (electorate,
    list, total)}) for the preliminary and projected party votes."""
    names = PartyNames()
    prelim_2023 = names.to_ids("2023", read_overview(PRELIM_2023_OVERVIEW))
    final_2023 = names.to_ids("2023", read_party_totals(FINAL_2023_PARTY_VOTES))
    prelim_2026_by_name = read_party_totals(PRELIM_2026_PARTY_VOTES)
    prelim_2026 = names.to_ids("2026", prelim_2026_by_name)
    display_names = {names.party_id("2026", name): name for name in prelim_2026_by_name}

    unmatched = set(prelim_2023) ^ set(final_2023)
    if unmatched:
        raise ValueError("2023 preliminary and final parties don't match: {0}".format(sorted(unmatched)))

    # Steps 1 and 3: 2023 multipliers and adjustment
    specials_2023 = Counter({p: final_2023[p] - prelim_2023[p] for p in final_2023})
    prelim_share_2023 = shares(prelim_2023)
    special_share_2023 = shares(specials_2023)
    multipliers_2023 = {p: special_share_2023[p] / prelim_share_2023[p] for p in final_2023}
    adjustment = sum(specials_2023.values()) / SPECIAL_ESTIMATE_2023
    projected_specials_total = SPECIAL_ESTIMATE_2026 * adjustment

    # Step 2: projected 2026 special-vote shares
    prelim_share_2026 = shares(prelim_2026)
    links = {p: names.counterpart(p, "2023", final_2023) for p in prelim_2026}
    multipliers = {p: multipliers_2023[links[p]] if links[p] else 1.0 for p in prelim_2026}
    unnormalised = {p: prelim_share_2026[p] * multipliers[p] for p in prelim_2026}
    norm = sum(unnormalised.values())
    special_share_2026 = {p: s / norm for p, s in unnormalised.items()}

    # Step 4: projected final count
    specials_2026 = {p: special_share_2026[p] * projected_specials_total for p in prelim_2026}
    final_2026 = {p: prelim_2026[p] + specials_2026[p] for p in prelim_2026}

    # Step 5: seats
    electorates, other_electorates = electorate_winners(PRELIM_2026_CANDIDATE_VOTES, "2026", names, prelim_2026)
    prelim_seats = allocate(prelim_2026, electorates, other_electorates)
    final_seats = allocate(final_2026, electorates, other_electorates)

    return {
        "names": names, "display_names": display_names,
        "prelim_2023": prelim_2023, "final_2023": final_2023, "specials_2023": specials_2023,
        "prelim_share_2023": prelim_share_2023, "special_share_2023": special_share_2023,
        "multipliers_2023": multipliers_2023, "adjustment": adjustment,
        "estimate_2023": SPECIAL_ESTIMATE_2023, "estimate_2026": SPECIAL_ESTIMATE_2026,
        "projected_specials_total": projected_specials_total,
        "prelim_2026": prelim_2026, "prelim_share_2026": prelim_share_2026, "links": links,
        "multipliers": multipliers, "special_share_2026": special_share_2026,
        "specials_2026": specials_2026, "final_2026": final_2026,
        "electorates": electorates, "other_electorates": other_electorates,
        "prelim_seats": prelim_seats, "final_seats": final_seats,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default="results/projection-2026/national.csv")
    args = parser.parse_args()

    c = compute()
    names, links, prelim_2026 = c["names"], c["links"], c["prelim_2026"]
    prelim_seats, final_seats = c["prelim_seats"], c["final_seats"]
    other_electorates, display_names = c["other_electorates"], c["display_names"]
    final_total = sum(c["final_2026"].values())

    rows = []
    parties = sorted(prelim_2026, key=lambda p: -prelim_2026[p])
    for party in parties:
        rows.append([names.short_names[party], links[party] or "", prelim_2026[party],
                     100 * c["prelim_share_2026"][party], c["multipliers"][party],
                     100 * c["special_share_2026"][party], c["specials_2026"][party], c["final_2026"][party],
                     100 * c["final_2026"][party] / final_total,
                     prelim_seats[party][2], final_seats[party][0], final_seats[party][1], final_seats[party][2]])

    print("2023: preliminary {0:,}, final {1:,}, special votes {2:,}, estimate {3:,}, adjustment {4:.4f}".format(
        sum(c["prelim_2023"].values()), sum(c["final_2023"].values()), sum(c["specials_2023"].values()),
        SPECIAL_ESTIMATE_2023, c["adjustment"]))
    print("2026: preliminary {0:,}, estimate {1:,}, projected special votes {2:,.0f}, projected final {3:,.0f}".format(
        sum(prelim_2026.values()), SPECIAL_ESTIMATE_2026, c["projected_specials_total"], final_total))
    print()
    print("{0:<20} {1:>9} {2:>7} {3:>6} {4:>7} {5:>8} {6:>9} {7:>7}  {8:>6} {9:>4} {10:>4} {11:>5}".format(
        "party", "prelim", "prel%", "mult", "spec%", "specials", "final", "final%",
        "prelim", "elec", "list", "final"))
    print(" " * 75 + "seats:")
    for r in rows:
        print("{0:<20} {2:>9,} {3:>7.2f} {4:>6.3f} {5:>7.2f} {6:>8,.0f} {7:>9,.0f} {8:>7.2f}  "
              "{9:>6} {10:>4} {11:>4} {12:>5}".format(*r))
    print("{0:<20} {1:>66} {2:>4} {3:>4} {4:>5}".format(
        "total", sum(r[9] for r in rows), sum(r[10] for r in rows), sum(r[11] for r in rows),
        sum(r[12] for r in rows)))
    if other_electorates:
        print("plus {0} electorate(s) won by independents or parties without a list".format(other_electorates))
    for label, seats in [("preliminary", prelim_seats), ("projected", final_seats)]:
        house = sum(s[2] for s in seats.values()) + other_electorates
        print("{0}: {1} seats, overhang {2}, majority {3}".format(label, house, house - TOTAL_SEATS, house // 2 + 1))
    no_link = [r[0] for r in rows if not r[1]]
    print()
    print("multiplier 1 (no 2023 counterpart): " + ", ".join(no_link))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["party_id", "short_name", "name", "party_id_2023", "prelim_votes", "prelim_pct", "multiplier",
                         "projected_special_pct", "projected_special_votes", "projected_final_votes",
                         "projected_final_pct", "prelim_seats", "projected_electorate_seats",
                         "projected_list_seats", "projected_seats"])
        for party, r in zip(parties, rows):
            writer.writerow([party, r[0], display_names[party]] + r[1:3] + ["{0:.4f}".format(r[3]), "{0:.4f}".format(r[4]), "{0:.4f}".format(r[5]),
                                     "{0:.0f}".format(r[6]), "{0:.0f}".format(r[7]), "{0:.4f}".format(r[8])] + r[9:])
    print("wrote {0} ({1} rows)".format(args.output, len(rows)))


if __name__ == "__main__":
    main()
