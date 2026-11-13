"""Projects the 2026 final count in each electorate, for both the party vote
and the electorate (candidate) vote, by applying 2023's special votes to the
2026 preliminary count. Per-electorate version of project_specials.py.

As there, "special votes" means final minus preliminary valid votes, which also
includes changes to ordinary votes in the official count.

  1. Notional 2023 counts. Each 2026 electorate's 2023 preliminary and final
     counts are the sums of its 2023 source electorates' counts, each weighted
     by the share of that 2023 electorate's electoral population that's in
     the 2026 electorate (concordance.py). This assumes votes are spread
     evenly over each 2023 electorate's population.
  2. Multipliers. For each party, in each 2026 electorate, the multiplier is
     its share of the notional special votes divided by its share of the
     notional preliminary count, separately for party votes and candidate
     votes. Candidates are matched by party (party_names.toml). A candidate
     whose party had no 2023 candidate there uses that party's party-vote
     multiplier in the same electorate. An independent, or a candidate from a
     party with no list, gets a multiplier of 1.
  3. Special-vote volume. Each 2026 electorate's special votes are its 2026
     preliminary count times its notional 2023 ratio of special votes to
     preliminary votes, times one national scale factor. The factor makes the
     party votes add up to the national projection's total (the Electoral
     Commission's estimate times the 2023 adjustment; see project_specials.py).
     The same factor is used for candidate votes.
  4. Projected special votes are shared out as in project_specials.py: the
     2026 preliminary share times the multiplier, normalised.
  5. Seats are allocated from the national projection's party votes
     (results/projection-2026/national.csv, from project_specials.py) and the
     projected electorate winners.

Port Waikato is left out: 2023 had no general-election electorate vote
there (the poll was cancelled and it went to a by-election), and its
preliminary page wasn't archived. Its boundaries didn't change in 2025, so
only the 2026 Port Waikato electorate is affected. In step 3 it's counted at
the national 2023 ratio, and in step 5 at its preliminary winner.

Inputs: results/concordance/electorates_2023_2026.csv (concordance.py),
results/2023-prelim/ (scrape_wayback_prelim.py), results/2023/ and
results/2026-prelim/ (download.py), results/projection-2026/national.csv
(project_specials.py) and the 2023 preliminary overview page (NOTES.md).
"""
import argparse
import csv
import os
from collections import Counter, defaultdict

from parties import PartyNames
from project_specials import (PRELIM_2023_OVERVIEW, SPECIAL_ESTIMATE_2023, SPECIAL_ESTIMATE_2026,
                              read_overview, read_party_totals)
from seats import TOTAL_SEATS, allocate

CONCORDANCE = "results/concordance/electorates_2023_2026.csv"
NATIONAL_PROJECTION = "results/projection-2026/national.csv"
OMITTED_2023 = {39}  # Port Waikato
FILES = {
    ("2023", "prelim", "party"): "results/2023-prelim/party_votes.csv",
    ("2023", "final", "party"): "results/2023/party_votes.csv",
    ("2023", "prelim", "candidate"): "results/2023-prelim/candidate_votes.csv",
    ("2023", "final", "candidate"): "results/2023/candidate_votes.csv",
    ("2026", "prelim", "party"): "results/2026-prelim/party_votes.csv",
    ("2026", "prelim", "candidate"): "results/2026-prelim/candidate_votes.csv",
}
NOTABLE_SHARE = 0.05  # report candidates with multiplier 1 above this share
CLOSE_MARGIN = 0.05   # report electorates with a projected margin below this


def read_votes(filename, election, names, kind):
    """Returns ({elec_id: {key: votes}}, {elec_id: name}, {(elec_id, key): label}).
    For party votes, key is the party_id. For candidate votes, key is the
    candidate's party_id, or ("other", candidate) for an independent or a
    party not in party_names.toml (one with no list)."""
    votes = defaultdict(Counter)
    elec_names = {}
    labels = {}
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            elec_id = int(row["elec_id"])
            elec_names[elec_id] = row["elec_name"]
            if kind == "party":
                key = names.party_id(election, row["party"])
            else:
                key = names.ids.get((election, row["party"]), ("other", row["candidate"]))
                labels[(elec_id, key)] = "{0} ({1})".format(row["candidate"], row["party"].strip())
            votes[elec_id][key] += int(row["votes"])
    return votes, elec_names, labels


def read_concordance(filename):
    """Returns {elec_id_2026: [(elec_id_2023, share_of_2023, share_of_2026)]}."""
    sources = defaultdict(list)
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sources[int(row["elec_id_2026"])].append(
                (int(row["elec_id_2023"]), float(row["share_of_2023"]), float(row["share_of_2026"])))
    return sources


def notional(sources, votes_2023):
    """Weighted sum of 2023 counts over a 2026 electorate's sources."""
    result = Counter()
    for elec_id, weight, _ in sources:
        for key, votes in votes_2023[elec_id].items():
            result[key] += weight * votes
    return result


def multipliers_2023(prelim_n, final_n):
    """{2023 key: share of notional special votes / share of notional
    preliminary votes}, for keys with preliminary votes."""
    total_prelim = sum(prelim_n.values())
    total_specials = sum(final_n.values()) - total_prelim
    return {k: ((final_n.get(k, 0) - v) / total_specials) / (v / total_prelim)
            for k, v in prelim_n.items() if v > 0}


def project(prelim_2026, prelim_n, final_n, names, volume, fallback=None):
    """Shares `volume` special votes among the keys of prelim_2026. A key
    with no 2023 counterpart uses its multiplier in `fallback` ({2026 key:
    multiplier}) if there, else 1. Returns ({key: projected special votes},
    {key: multiplier}, {key: source}), where source is the 2023 key, "party
    vote" for a fallback, or None."""
    m_2023 = multipliers_2023(prelim_n, final_n)
    total_2026 = sum(prelim_2026.values())
    multipliers, links = {}, {}
    for key in prelim_2026:
        link = None if isinstance(key, tuple) else names.counterpart(key, "2023", m_2023)
        if link:
            links[key], multipliers[key] = link, m_2023[link]
        elif fallback and key in fallback:
            links[key], multipliers[key] = "party vote", fallback[key]
        else:
            links[key], multipliers[key] = None, 1.0
    unnormalised = {k: prelim_2026[k] / total_2026 * multipliers[k] for k in prelim_2026}
    norm = sum(unnormalised.values())
    return {k: volume * u / norm for k, u in unnormalised.items()}, multipliers, links


def special_ratio(prelim_n, final_n):
    return (sum(final_n.values()) - sum(prelim_n.values())) / sum(prelim_n.values())


def winner(votes):
    ranked = sorted(votes, key=lambda k: -votes[k])
    if len(ranked) > 1 and votes[ranked[0]] == votes[ranked[1]]:
        raise ValueError("tie for first: {0}".format(ranked[:2]))
    return ranked[0], ranked[1]


def compute():
    """Runs the projection. Returns a dict with the inputs (`data`, `labels`,
    `sources`, ...), the national scale factor, and `electorates`: {2026
    elec_id: detail}, where detail has the electorate's live 2023 sources,
    omitted share and, for "party" and "candidate", the 2026 preliminary
    votes, notional 2023 preliminary and final votes, volume, ratio,
    multipliers, links, projected special votes and projected final votes.
    Candidate details also have the preliminary and projected winner and
    runner-up. Electorates with no live sources (Port Waikato) are in
    `omitted` instead."""
    names = PartyNames()
    data, elec_names, labels = {}, {}, {}
    for (election, stage, kind), filename in FILES.items():
        data[(election, stage, kind)], en, lb = read_votes(filename, election, names, kind)
        elec_names[election] = en
        labels.update(lb) if election == "2026" else None
    for kind in ["party", "candidate"]:
        prelim_ids = set(data[("2023", "prelim", kind)])
        final_ids = set(data[("2023", "final", kind)]) - OMITTED_2023
        if prelim_ids != final_ids:
            raise ValueError("2023 {0} votes: preliminary and final electorates differ: {1}".format(
                kind, sorted(prelim_ids ^ final_ids)))
    sources = read_concordance(CONCORDANCE)
    if set(sources) != set(data[("2026", "prelim", "party")]):
        raise ValueError("concordance and 2026 electorates differ")

    # Step 3: national scale factor, as in project_specials.py.
    prelim_2023_national = names.to_ids("2023", read_overview(PRELIM_2023_OVERVIEW))
    final_2023_national = names.to_ids("2023", read_party_totals(FILES[("2023", "final", "party")]))
    national_specials_2023 = sum(final_2023_national.values()) - sum(prelim_2023_national.values())
    national_ratio = national_specials_2023 / sum(prelim_2023_national.values())
    target = SPECIAL_ESTIMATE_2026 * national_specials_2023 / SPECIAL_ESTIMATE_2023

    projected, omitted, ratios, unscaled = [], [], {}, 0.0
    for elec_id in sorted(sources):
        live = [s for s in sources[elec_id] if s[0] not in OMITTED_2023]
        omitted_share = sum(s[2] for s in sources[elec_id] if s[0] in OMITTED_2023)
        if not live:
            omitted.append(elec_id)
        prelim_party_2026 = data[("2026", "prelim", "party")][elec_id]
        ratios[elec_id] = {}
        for kind in ["party", "candidate"]:
            if live:
                ratios[elec_id][kind] = special_ratio(notional(live, data[("2023", "prelim", kind)]),
                                                      notional(live, data[("2023", "final", kind)]))
            else:
                ratios[elec_id][kind] = national_ratio
        unscaled += sum(prelim_party_2026.values()) * ratios[elec_id]["party"]
        if live:
            projected.append((elec_id, live, omitted_share))
    scale = target / unscaled

    details, winners_prelim, winners_final = {}, {}, {}
    for elec_id, live, omitted_share in projected:
        detail = {"name": elec_names["2026"][elec_id], "live": live, "omitted_share": omitted_share}
        for kind in ["party", "candidate"]:
            prelim_2026 = data[("2026", "prelim", kind)][elec_id]
            prelim_n = notional(live, data[("2023", "prelim", kind)])
            final_n = notional(live, data[("2023", "final", kind)])
            volume = sum(prelim_2026.values()) * ratios[elec_id][kind] * scale
            specials, multipliers, links = project(prelim_2026, prelim_n, final_n, names, volume,
                                                   detail["party"]["multipliers"] if kind == "candidate" else None)
            final = {k: prelim_2026[k] + specials[k] for k in prelim_2026}
            detail[kind] = {"prelim_2026": prelim_2026, "prelim_n": prelim_n, "final_n": final_n,
                            "ratio": ratios[elec_id][kind], "volume": volume, "specials": specials,
                            "multipliers": multipliers, "links": links, "final": final}
        cand = detail["candidate"]
        cand["prelim_winner"], cand["prelim_second"] = winner(cand["prelim_2026"])
        cand["winner"], cand["second"] = winner(cand["final"])
        winners_prelim[elec_id], winners_final[elec_id] = cand["prelim_winner"], cand["winner"]
        details[elec_id] = detail
    for elec_id in omitted:  # held at the preliminary winner
        p1, _ = winner(data[("2026", "prelim", "candidate")][elec_id])
        winners_prelim[elec_id] = winners_final[elec_id] = p1

    return {"names": names, "data": data, "elec_names": elec_names, "labels": labels, "sources": sources,
            "national_ratio": national_ratio, "target": target, "scale": scale, "ratios": ratios,
            "electorates": details, "omitted": omitted,
            "winners_prelim": winners_prelim, "winners_final": winners_final}


def seats_from(party_votes, won):
    """Allocates seats from {party_id: votes} and {elec_id: winning key}.
    Returns (seats, other electorates)."""
    electorates = Counter(k for k in won.values() if not isinstance(k, tuple) and k in party_votes)
    other = sum(1 for k in won.values() if isinstance(k, tuple) or k not in party_votes)
    return allocate(party_votes, electorates, other), other


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outdir", default="results/projection-2026")
    args = parser.parse_args()

    c = compute()
    names, labels, data, elec_names = c["names"], c["labels"], c["data"], c["elec_names"]
    omitted, scale, target, national_ratio = c["omitted"], c["scale"], c["target"], c["national_ratio"]
    winners_prelim, winners_final = c["winners_prelim"], c["winners_final"]

    party_rows, candidate_rows, summary = [], [], []
    for elec_id, detail in c["electorates"].items():
        name = detail["name"]
        for kind, rows in [("party", party_rows), ("candidate", candidate_rows)]:
            d = detail[kind]
            prelim_2026, multipliers, links = d["prelim_2026"], d["multipliers"], d["links"]
            specials, final, volume = d["specials"], d["final"], d["volume"]
            total_final = sum(final.values())
            for key in sorted(prelim_2026, key=lambda k: -final[k]):
                label = labels[(elec_id, key)] if kind == "candidate" else names.short_names[key]
                rows.append([elec_id, name, key if not isinstance(key, tuple) else "", label,
                             links[key] or "", prelim_2026[key], "{0:.4f}".format(multipliers[key]),
                             "{0:.0f}".format(specials[key]), "{0:.0f}".format(final[key]),
                             "{0:.4f}".format(100 * final[key] / total_final)])
            if kind == "candidate":
                notable = [labels[(elec_id, k)] + ("" if links[k] is None else " [party-vote multiplier {0:.3f}]".format(
                               multipliers[k])) for k in prelim_2026
                           if links[k] in (None, "party vote") and final[k] / total_final > NOTABLE_SHARE]
                p1, p2, f1, f2 = d["prelim_winner"], d["prelim_second"], d["winner"], d["second"]
                summary.append({
                    "elec_id": elec_id, "name": name, "omitted_share": detail["omitted_share"],
                    "prelim_winner": labels[(elec_id, p1)], "prelim_margin": prelim_2026[p1] - prelim_2026[p2],
                    "prelim_margin_pct": (prelim_2026[p1] - prelim_2026[p2]) / sum(prelim_2026.values()),
                    "projected_winner": labels[(elec_id, f1)], "projected_second": labels[(elec_id, f2)],
                    "projected_margin": final[f1] - final[f2],
                    "projected_margin_pct": (final[f1] - final[f2]) / total_final,
                    "projected_specials": volume, "flips": p1 != f1, "no_2023_counterpart": "; ".join(notable)})

    os.makedirs(args.outdir, exist_ok=True)
    header = ["elec_id", "elec_name", "party_id", "name", "party_id_2023", "prelim_votes", "multiplier",
              "projected_special_votes", "projected_final_votes", "projected_final_pct"]
    for filename, rows in [("electorates_party.csv", party_rows), ("electorates_candidate.csv", candidate_rows)]:
        with open(os.path.join(args.outdir, filename), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    summary.sort(key=lambda s: s["projected_margin_pct"])
    with open(os.path.join(args.outdir, "electorates_summary.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        for s in summary:
            # Votes to whole numbers; shares as percentages to 4 decimals, as in the other files.
            writer.writerow(dict(s, **{k: "{0:.0f}".format(s[k]) for k in ["projected_margin", "projected_specials"]},
                                 **{k: "{0:.4f}".format(100 * s[k]) for k in
                                    ["omitted_share", "prelim_margin_pct", "projected_margin_pct"]}))

    # Report
    print("scale factor {0:.4f}: projected special party votes {1:,.0f} (national projection {2:,.0f})".format(
        scale, sum(float(r[7]) for r in party_rows) + sum(
            sum(data[("2026", "prelim", "party")][e].values()) * national_ratio * scale for e in omitted), target))
    print("projected special candidate votes {0:,.0f}".format(sum(float(r[7]) for r in candidate_rows)))
    print("not projected (all 2023 sources omitted): " + ", ".join(elec_names["2026"][e] for e in omitted))
    partly = [(s["name"], s["omitted_share"]) for s in summary if s["omitted_share"] > 0]
    if partly:
        print("partly from omitted 2023 electorates: " + ", ".join("{0} ({1:.1%})".format(*p) for p in partly))
    print()
    print("Electorates projected to flip, or with a projected margin under {0:.0%}:".format(CLOSE_MARGIN))
    print("{0:<24} {1:<34} {2:>7} {3:>6}   {4:<34} {5:>7} {6:>6}  {7}".format(
        "electorate", "preliminary leader", "margin", "%", "projected winner", "margin", "%", "projected second"))
    for s in summary:
        if s["flips"] or s["projected_margin_pct"] < CLOSE_MARGIN:
            print("{0:<24} {1:<34} {2:>7,} {3:>5.1f}%   {4:<34} {5:>7,.0f} {6:>5.1f}%  {7}{8}".format(
                s["name"], s["prelim_winner"][:34], s["prelim_margin"], 100 * s["prelim_margin_pct"],
                s["projected_winner"][:34], s["projected_margin"], 100 * s["projected_margin_pct"],
                s["projected_second"], "   <-- FLIPS" if s["flips"] else ""))
    notable = [(s["name"], s["no_2023_counterpart"]) for s in summary if s["no_2023_counterpart"]]
    if notable:
        print()
        print("candidates over {0:.0%} with no 2023 candidate counterpart (multiplier 1 unless shown):".format(
            NOTABLE_SHARE))
        for n, c in notable:
            print("  {0}: {1}".format(n, c))

    # Step 5: seats
    with open(NATIONAL_PROJECTION, newline="", encoding="utf-8") as f:
        party_votes = {row["party_id"]: float(row["projected_final_votes"]) for row in csv.DictReader(f)}
    print()
    for label, won in [("preliminary electorates", winners_prelim), ("projected electorates", winners_final)]:
        seats, other = seats_from(party_votes, won)
        house = sum(s[2] for s in seats.values()) + other
        print("projected party vote, {0}: {1} seats (overhang {2}, majority {3}): {4}".format(
            label, house, house - TOTAL_SEATS, house // 2 + 1, ", ".join(
                "{0} {1}".format(names.short_names[p], s[2]) for p, s in
                sorted(seats.items(), key=lambda x: -x[1][2]) if s[2])))
    print("wrote electorates_party.csv, electorates_candidate.csv, electorates_summary.csv in " + args.outdir)


if __name__ == "__main__":
    main()
