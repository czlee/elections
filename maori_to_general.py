"""What the 2026 preliminary electorate results would have been with no Māori
electorates, if every Māori-roll voter had voted in the general electorate.

  1. Voters follow their voting places. Each Māori electorate's votes at a
     voting place (download_maori_places.py) are added to the general
     electorate the place is in (the place's vp_e_no, which is a general
     electorate for every place that took Māori-electorate votes).
  2. Each Māori-electorate candidate's votes go to the candidate of the same
     party in that general electorate. Exceptions:
       - Te Pāti Māori, Te Tai Tokerau Party and Tākuta Ferris (independent,
         Te Tai Tonga) go to Labour.
       - Independents are discarded.
       - A party with no candidate in that general electorate goes to the
         major party of its bloc (BLOC_MAJOR: Green to Labour, NZ First and
         ACT to National).
       - A party with neither a candidate there nor a bloc (BLOC_MAJOR) is
         discarded and reported: Legalise Cannabis, Opportunity, NZ Loyal, Your
         PIC Party (not in the bloc map on purpose; nothing is silent).
     Every redirect and discard is tallied in the output, with the number of
     votes, so a case that matters can't go unnoticed.

Party votes are unchanged. Seats are re-allocated with seats.py from the
preliminary party votes and the new electorate winners, 120 seats and no
Māori electorates, with the 5% threshold waived for Māori parties
(THRESHOLD_WAIVED). Compares with the preliminary winners (not the projected
final result; specials aren't involved).

Inputs: results/2026-prelim/ (download.py), and the voting-place files from
download_maori_places.py. Outputs to results/maori-to-general/:
electorates.csv (every general electorate: old and new winner and margin),
redirects.csv (what happened to Māori-roll votes, by party and treatment).
"""
import csv
import os
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from seats import allocate

PRELIM = "results/2026-prelim"
RAW = os.path.join(PRELIM, "raw")
OUT = "results/maori-to-general"
MAORI = range(65, 72)
# Tākuta Ferris, an independent (the 2023 Te Pāti Māori winner in Te Tai Tonga)
# in Te Pāti Māori's bloc, is treated as a party of his own so that his votes
# aren't dropped with the other independents.
FERRIS = "Tākuta Ferris"
# The 1986 Royal Commission on the Electoral System suggested abolishing the
# Māori electorates and waiving the party-vote threshold for parties
# primarily representing Māori interests. With no Māori electorates, we apply
# that: these parties qualify for list seats whatever their party vote.
THRESHOLD_WAIVED = {"Te Pāti Māori", "Te Tai Tokerau Party"}
FERRIS_CANDIDATE = "FERRIS, Tākuta"
TO_LABOUR = {"Te Pāti Māori", "Te Tai Tokerau Party", FERRIS}
INDEPENDENT = "Independent"
BLOC_MAJOR = {"Green Party": "Labour Party", "New Zealand First Party": "National Party",
              "ACT New Zealand": "National Party"}


def read_candidates():
    """Returns {c_no: party short name} from candidates.xml and parties.xml."""
    parties = {p.get("p_no"): p.findtext("short_name") for p in ET.parse(os.path.join(RAW, "parties.xml")).getroot()}
    parties["0"] = INDEPENDENT
    return {c.get("c_no"): FERRIS if c.findtext("candidate_name") == FERRIS_CANDIDATE else parties[c.findtext("party")]
            for c in ET.parse(os.path.join(RAW, "candidates.xml")).getroot()}


def read_general():
    """Returns ({e_no: name}, {e_no: {party: votes}}) for the general electorates. Each has
    one candidate per party at most, which is checked."""
    names, votes = {}, defaultdict(dict)
    with open(os.path.join(PRELIM, "candidate_votes.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            e = int(r["elec_id"])
            if e in MAORI:
                continue
            names[e] = r["elec_name"]
            if r["party"] in votes[e] and r["party"] != INDEPENDENT:
                raise ValueError("two {0} candidates in {1}".format(r["party"], r["elec_name"]))
            votes[e][r["party"]] = votes[e].get(r["party"], 0) + int(r["votes"])
    return names, votes


def read_places(c_party):
    """Returns [(maori e_no, home general e_no, {party: votes})], one per
    voting-place file."""
    places = []
    for e in MAORI:
        directory = os.path.join(RAW, "e{0:02d}".format(e), "votingplaces")
        for filename in sorted(os.listdir(directory)):
            root = ET.parse(os.path.join(directory, filename)).getroot()
            assert int(root.get("e_no")) == e, filename
            home = int(root.get("vp_e_no"))
            if home in MAORI:
                raise ValueError("{0}: home electorate {1} is a Māori electorate".format(filename, home))
            totals = Counter()
            for c in root.find("candidatevotes"):
                totals[c_party[c.get("c_no")]] += int(c.findtext("votes"))
            places.append((e, home, totals))
    return places


def check_totals(places):
    """The voting places should add up to each Māori electorate's total."""
    for e in MAORI:
        root = ET.parse(os.path.join(RAW, "e{0:02d}".format(e), "e{0:02d}.xml".format(e))).getroot()
        total = sum(int(c.findtext("votes")) for c in root.find("candidatevotes"))
        got = sum(sum(t.values()) for pe, _, t in places if pe == e)
        if got != total:
            raise ValueError("e{0:02d}: voting places have {1} candidate votes, electorate total {2}".format(e, got, total))


def project(general, places, labour_share=1.0):
    """Returns ({e_no: {party: votes}} with the Māori-roll votes added, a
    Counter of (party, treatment) -> votes, and a Counter of
    (general e_no, Māori e_no, party, treatment, target party or None) -> votes).

    labour_share is the share of the TO_LABOUR parties' votes (Te Pāti Māori,
    Te Tai Tokerau Party and Tākuta Ferris, treated as one group) that go to
    Labour; the rest are dropped (they'd stay home or vote for someone else we can't
    identify). The default is 1, the assumption in the module docstring.
    """
    new = {e: dict(v) for e, v in general.items()}
    log, detail = Counter(), Counter()
    for maori, home, totals in places:
        for party, n in totals.items():
            if n == 0:
                continue
            if party in TO_LABOUR and labour_share != 1:
                dropped = n - n * labour_share
                n = n * labour_share
                log[(party, "dropped: not to Labour")] += dropped
            if party == INDEPENDENT:
                target, how = None, "discarded: independent"
            elif party in TO_LABOUR:
                target, how = "Labour Party", "to Labour"
            elif party in general[home]:
                target, how = party, "same party"
            elif party in BLOC_MAJOR and BLOC_MAJOR[party] in general[home]:
                target, how = BLOC_MAJOR[party], "to bloc major party (no candidate there)"
            else:
                target, how = None, "discarded: no candidate there and no bloc"
            if target in TO_LABOUR or (target and target not in general[home]):
                raise ValueError("no {0} candidate in electorate {1}".format(target, home))
            if target:
                new[home][target] += n
            log[(party, how)] += n
            detail[(home, maori, party, how, target)] += n
    return new, log, detail


def winner(votes):
    ranked = sorted(votes.items(), key=lambda x: -x[1])
    return ranked[0][0], ranked[0][1] - ranked[1][1]


def main():
    c_party = read_candidates()
    names, general = read_general()
    places = read_places(c_party)
    check_totals(places)
    new, log, _ = project(general, places)

    os.makedirs(OUT, exist_ok=True)
    flips, wins_old, wins_new = [], Counter(), Counter()
    rows = []
    for e in sorted(names):
        w0, m0 = winner(general[e])
        w1, m1 = winner(new[e])
        moved = sum(new[e].values()) - sum(general[e].values())
        wins_old[w0] += 1
        wins_new[w1] += 1
        rows.append([e, names[e], w0, m0, w1, m1, moved, "flip" if w0 != w1 else ""])
        if w0 != w1:
            flips.append((names[e], w0, w1, m1))
    with open(os.path.join(OUT, "electorates.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["elec_id", "elec_name", "winner_prelim", "margin_prelim", "winner_new", "margin_new",
                    "votes_added", "flip"])
        w.writerows(rows)
    with open(os.path.join(OUT, "redirects.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["maori_party", "treatment", "votes"])
        for (party, how), n in sorted(log.items(), key=lambda x: -x[1]):
            w.writerow([party, how, n])

    print("Māori-roll candidate votes redistributed (party, treatment, votes):")
    for (party, how), n in sorted(log.items(), key=lambda x: -x[1]):
        print("  {0:<35} {1:<45} {2:>7}".format(party, how, n))
    print("\nFlips: {0} of {1} general electorates".format(len(flips), len(names)))
    for name, w0, w1, m1 in flips:
        print("  {0:<22} {1} -> {2} (new margin {3})".format(name, w0, w1, m1))
    print("\nElectorate wins (prelim -> no Māori seats):")
    for p in sorted(set(wins_old) | set(wins_new)):
        print("  {0:<25} {1:>3} -> {2:>3}".format(p, wins_old[p], wins_new[p]))
    print("\nClosest new margins:")
    for r in sorted(rows, key=lambda r: r[5])[:8]:
        print("  {0:<22} {1} by {2}{3}".format(r[1], r[4], r[5], "  (flipped)" if r[7] else ""))

    # Seats: party votes are unchanged. The old result has the 7 Māori seats.
    votes = {}
    with open(os.path.join(PRELIM, "party_votes.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            votes[r["party"]] = votes.get(r["party"], 0) + int(r["votes"])
    old_won = Counter()
    with open(os.path.join(PRELIM, "candidate_votes.csv"), encoding="utf-8") as f:
        by_e = defaultdict(dict)
        for r in csv.DictReader(f):
            by_e[int(r["elec_id"])][r["party"]] = by_e[int(r["elec_id"])].get(r["party"], 0) + int(r["votes"])
    for e, v in by_e.items():
        old_won[winner(v)[0]] += 1
    print("\nSeats (prelim party votes; electorates won -> total):")
    for label, won, waived in [("as counted", old_won, ()), ("no Māori seats, threshold waived", wins_new, THRESHOLD_WAIVED),
                               ("no Māori seats, no waiver", wins_new, ())]:
        eligible = {p: n for p, n in won.items() if p in votes}
        other = sum(n for p, n in won.items() if p not in votes)
        result = allocate(votes, eligible, other, waived=waived)
        print("  {0}: {1} seats".format(label, sum(r[2] for r in result.values()) + other))
        for p, (e_won, lst, tot) in sorted(result.items(), key=lambda x: -x[1][2]):
            if tot:
                print("    {0:<25} {1:>3} electorate + {2:>3} list = {3:>3}".format(p, e_won, lst, tot))
        if other:
            print("    (+{0} won by others)".format(other))


if __name__ == "__main__":
    main()
