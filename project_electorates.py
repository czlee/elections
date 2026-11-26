"""Projects the 2026 final count in each electorate, for both the party vote
and the electorate (candidate) vote, by applying a base election's special
votes to the 2026 preliminary count. Per-electorate version of
project_specials.py, with the same three pools: overseas and domestic special
votes, and revisions (the official count's corrections to the preliminary
count).

  1. Notional base counts. Each 2026 electorate's base-year final count, and
     its ordinary, overseas and domestic votes (download_specials.py), are
     the sums of its base source electorates' counts, each weighted by the
     share of that base electorate's electoral population that's in the 2026
     electorate (concordance.py). This assumes votes are spread evenly over
     each base electorate's population.
  2. Multipliers. For each party, in each 2026 electorate, the overseas and
     domestic multipliers are its share of the notional pool divided by its
     share of the notional ordinary votes, separately for party votes and
     candidate votes. Candidates are matched by party (party_names.toml). A
     candidate whose party had no base candidate there uses that party's
     party-vote multiplier for the same pool in the same electorate. An
     independent, or a candidate from a party with no list, gets 1.
  3. Volumes. Each 2026 electorate's overseas (domestic) votes are its 2026
     preliminary count times its notional ratio of overseas (domestic) to
     ordinary votes, times a national scale factor for the pool. The factor
     makes the party votes add up to the national projection's pool
     (project_specials.py); the same factor is used for candidate votes.
     Revisions are the 2026 preliminary count times the national revisions
     ratio, the same in every electorate. Electorates' own revisions barely
     carry over from one election to the next, so they aren't used
     (NOTES.md).
  4. Each pool is shared out as in project_specials.py: the 2026 preliminary
     share times the multiplier (1 for revisions), normalised.
  5. Seats are allocated from the national projection's party votes
     (results/projection-2026/national.csv, from project_specials.py) and the
     projected electorate winners.

The base election is 2023 by default, or 2017 or 2020 with --base. Base-year
preliminary counts aren't needed per electorate, so 2020 (whose weren't
archived) works too.

Port Waikato is left out of the 2023 base: 2023 had no general-election
electorate vote there (the poll was cancelled and it went to a by-election).
Its boundaries didn't change in 2025, so only the 2026 Port Waikato electorate
is affected. In step 3 it's counted at the national ratios, and in step 5 at
its preliminary winner. Nothing is left out of the 2017 and 2020 bases.

Inputs: results/concordance/electorates_<base>_2026.csv (concordance.py),
results/<base>/ (download.py and download_specials.py), results/2026-prelim/
(download.py), and project_specials.py's inputs (it's run for the national
pools), and results/projection-2026/national.csv or national-base<base>.csv
(project_specials.py) for seats.
"""
import argparse
import csv
import os
from collections import Counter, defaultdict

import project_specials as ps
from parties import PartyNames
from project_specials import read_party_totals
from seats import TOTAL_SEATS, allocate

DEFAULT_BASE = "2023"
# Base elections with electorate projections, and the base electorates left out.
OMITTED = {"2017": set(), "2020": set(), "2023": {39}}  # 2023: Port Waikato
OMITTED_2023 = OMITTED["2023"]
CONCORDANCE = "results/concordance/electorates_2023_2026.csv"


def concordance_file(base):
    return "results/concordance/electorates_{0}_2026.csv".format(base)


def files(base):
    return {
        (base, "final", "party"): "results/{0}/party_votes.csv".format(base),
        (base, "final", "candidate"): "results/{0}/candidate_votes.csv".format(base),
        ("2026", "prelim", "party"): "results/2026-prelim/party_votes.csv",
        ("2026", "prelim", "candidate"): "results/2026-prelim/candidate_votes.csv",
    }


FILES = files(DEFAULT_BASE)


def output_name(filename, base):
    """electorates_party.csv for the default base, electorates_party-base2017.csv otherwise."""
    if base == DEFAULT_BASE:
        return filename
    stem, ext = os.path.splitext(filename)
    return "{0}-base{1}{2}".format(stem, base, ext)
CATEGORIES = ["ordinary", "overseas", "domestic"]
SPECIAL_POOLS = ["overseas", "domestic"]
NOTABLE_SHARE = 0.05  # report candidates with multiplier 1 above this share
CLOSE_MARGIN = 0.05   # report electorates with a projected margin below this


def vote_key(row, election, names, kind):
    """For party votes, the party_id. For candidate votes, the candidate's
    party_id, or ("other", candidate) for an independent or a party not in
    party_names.toml (one with no list)."""
    if kind == "party":
        return names.party_id(election, row["party"])
    return names.ids.get((election, row["party"]), ("other", row["candidate"]))


def read_votes(filename, election, names, kind):
    """Returns ({elec_id: {key: votes}}, {elec_id: name}, {(elec_id, key): label}),
    with keys as in vote_key()."""
    votes = defaultdict(Counter)
    elec_names = {}
    labels = {}
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            elec_id = int(row["elec_id"])
            elec_names[elec_id] = row["elec_name"]
            key = vote_key(row, election, names, kind)
            if kind == "candidate":
                labels[(elec_id, key)] = "{0} ({1})".format(row["candidate"], row["party"].strip())
            votes[elec_id][key] += int(row["votes"])
    return votes, elec_names, labels


def category_file(base, kind):
    return "results/{0}/{1}_votes_by_category.csv".format(base, kind)


def read_categories(filename, election, names, kind):
    """Reads a <kind>_votes_by_category.csv (download_specials.py). Returns
    {category: {elec_id: Counter({key: votes})}}, keys as in vote_key()."""
    votes = {c: defaultdict(Counter) for c in CATEGORIES}
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            votes[row["category"]][int(row["elec_id"])][vote_key(row, election, names, kind)] += int(row["votes"])
    return votes


def read_concordance(filename, base=DEFAULT_BASE):
    """Returns {elec_id_2026: [(elec_id_base, share_of_base, share_of_2026)]}."""
    sources = defaultdict(list)
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sources[int(row["elec_id_2026"])].append(
                (int(row["elec_id_" + base]), float(row["share_of_" + base]), float(row["share_of_2026"])))
    return sources


def notional(sources, votes_2023):
    """Weighted sum of 2023 counts over a 2026 electorate's sources."""
    result = Counter()
    for elec_id, weight, _ in sources:
        for key, votes in votes_2023[elec_id].items():
            result[key] += weight * votes
    return result


def pool_multipliers(pool_n, ordinary_n):
    """{base key: share of the notional pool / share of notional ordinary
    votes}, for keys with ordinary votes."""
    total_pool = sum(pool_n.values())
    total_ordinary = sum(ordinary_n.values())
    return {k: (pool_n.get(k, 0) / total_pool) / (v / total_ordinary)
            for k, v in ordinary_n.items() if v > 0}


def project(prelim_2026, m_base, names, volume, fallback=None, base=DEFAULT_BASE):
    """Shares one pool's `volume` among the keys of prelim_2026. A key with no
    base counterpart in `m_base` ({base key: multiplier}) uses its multiplier
    in `fallback` ({2026 key: multiplier}) if there, else 1. Returns ({key:
    projected votes}, {key: multiplier}, {key: source}), where source is the
    base key, "party vote" for a fallback, or None."""
    total_2026 = sum(prelim_2026.values())
    multipliers, links = {}, {}
    for key in prelim_2026:
        link = None if isinstance(key, tuple) else names.counterpart(key, base, m_base)
        if link:
            links[key], multipliers[key] = link, m_base[link]
        elif fallback and key in fallback:
            links[key], multipliers[key] = "party vote", fallback[key]
        else:
            links[key], multipliers[key] = None, 1.0
    _, specials = ps.project_pool({k: v / total_2026 for k, v in prelim_2026.items()}, multipliers, volume)
    return specials, multipliers, links


def winner(votes):
    ranked = sorted(votes, key=lambda k: -votes[k])
    if len(ranked) > 1 and votes[ranked[0]] == votes[ranked[1]]:
        raise ValueError("tie for first: {0}".format(ranked[:2]))
    return ranked[0], ranked[1]


def effective_multiplier(key, prelim_2026, specials, pools):
    """The key's projected share of all the pools' votes over its preliminary
    share. For a key with no preliminary votes (so no projected ones either),
    the pools' multipliers averaged by volume instead."""
    total_volume = sum(p["volume"] for p in pools.values())
    if prelim_2026[key] == 0:
        return sum(p["volume"] * p["multipliers"][key] for p in pools.values()) / total_volume
    return (specials[key] / total_volume) / (prelim_2026[key] / sum(prelim_2026.values()))


def compute(base=DEFAULT_BASE):
    """Runs the projection from base election `base`. Returns a dict with the
    inputs (`data`, `categories`, `labels`, `sources`, ...), the national
    `pools` (project_specials.compute()'s) and per-pool `scales`, and
    `electorates`: {2026 elec_id: detail}, where detail has the electorate's
    live base sources, omitted share and, for "party" and "candidate", the
    2026 preliminary votes, the notional base final and ordinary votes, and
    `pools` ({pool: notional base votes (overseas and domestic only), ratio,
    volume, multipliers, links and projected votes}), plus the pools'
    totals: volume, projected special votes, effective multipliers
    (projected special share / preliminary share) and projected final votes.
    Candidate details also have the preliminary and projected winner and
    runner-up. Electorates with no live sources (Port Waikato) are in
    `omitted` instead."""
    names = PartyNames()
    omitted_base = OMITTED[base]
    input_files = files(base)
    data, elec_names, labels = {}, {}, {}
    for (election, stage, kind), filename in input_files.items():
        data[(election, stage, kind)], en, lb = read_votes(filename, election, names, kind)
        elec_names[election] = en
        labels.update(lb) if election == "2026" else None
    categories = {kind: read_categories(category_file(base, kind), base, names, kind)
                  for kind in ["party", "candidate"]}
    for kind in ["party", "candidate"]:
        final_ids = set(data[(base, "final", kind)]) - omitted_base
        category_ids = set(categories[kind]["ordinary"]) - omitted_base
        if category_ids != final_ids:
            raise ValueError("{0} {1} votes: categories and final electorates differ: {2}".format(
                base, kind, sorted(category_ids ^ final_ids)))
    sources = read_concordance(concordance_file(base), base)
    if set(sources) != set(data[("2026", "prelim", "party")]):
        raise ValueError("concordance and 2026 electorates differ")

    # Step 3: volumes. Overseas and domestic: each electorate's 2026 preliminary
    # count times its notional base ratio of the pool to ordinary votes, times
    # a national scale factor for the pool, which makes the party votes add up
    # to the national projection's pool. Revisions: the national ratio.
    national = ps.compute(base)
    pools_national = national["pools"]
    revision_ratio = pools_national["revisions"]["adjustment"]
    party_cats = categories["party"]
    national_ratios = {pool: sum(sum(c.values()) for c in party_cats[pool].values()) /
                       sum(sum(c.values()) for c in party_cats["ordinary"].values()) for pool in SPECIAL_POOLS}

    notionals, omitted, unscaled = {}, [], Counter()
    for elec_id in sorted(sources):
        live = [s for s in sources[elec_id] if s[0] not in omitted_base]
        if not live:
            omitted.append(elec_id)
        prelim_party_2026 = sum(data[("2026", "prelim", "party")][elec_id].values())
        notionals[elec_id] = {}
        for kind in ["party", "candidate"]:
            if live:
                n = {c: notional(live, categories[kind][c]) for c in CATEGORIES}
                n["final"] = notional(live, data[(base, "final", kind)])
                n["ratio"] = {pool: sum(n[pool].values()) / sum(n["ordinary"].values()) for pool in SPECIAL_POOLS}
            else:
                n = {"ratio": national_ratios}
            notionals[elec_id][kind] = n
        for pool in SPECIAL_POOLS:
            unscaled[pool] += prelim_party_2026 * notionals[elec_id]["party"]["ratio"][pool]
    scales = {pool: pools_national[pool]["volume"] / unscaled[pool] for pool in SPECIAL_POOLS}

    details, winners_prelim, winners_final = {}, {}, {}
    for elec_id in sorted(sources):
        if elec_id in omitted:
            continue
        live = [s for s in sources[elec_id] if s[0] not in omitted_base]
        omitted_share = sum(s[2] for s in sources[elec_id] if s[0] in omitted_base)
        detail = {"name": elec_names["2026"][elec_id], "live": live, "omitted_share": omitted_share}
        for kind in ["party", "candidate"]:
            prelim_2026 = data[("2026", "prelim", kind)][elec_id]
            total_prelim = sum(prelim_2026.values())
            n = notionals[elec_id][kind]
            pools = {}
            for pool in SPECIAL_POOLS:
                volume = total_prelim * n["ratio"][pool] * scales[pool]
                fallback = detail["party"]["pools"][pool]["multipliers"] if kind == "candidate" else None
                specials, multipliers, links = project(prelim_2026, pool_multipliers(n[pool], n["ordinary"]),
                                                       names, volume, fallback, base)
                pools[pool] = {"notional": n[pool], "ratio": n["ratio"][pool], "volume": volume,
                               "specials": specials, "multipliers": multipliers, "links": links}
            # Step 2 for revisions: shared like the preliminary count.
            volume = total_prelim * revision_ratio
            pools["revisions"] = {"ratio": revision_ratio, "volume": volume,
                                  "specials": {k: volume * v / total_prelim for k, v in prelim_2026.items()},
                                  "multipliers": {k: 1.0 for k in prelim_2026}}
            specials = {k: sum(p["specials"][k] for p in pools.values()) for k in prelim_2026}
            volume = sum(p["volume"] for p in pools.values())
            final = {k: prelim_2026[k] + specials[k] for k in prelim_2026}
            detail[kind] = {"prelim_2026": prelim_2026, "ordinary_n": n["ordinary"], "final_n": n["final"],
                            "pools": pools, "volume": volume, "specials": specials, "final": final,
                            "links": pools["domestic"]["links"],
                            "multipliers": {k: effective_multiplier(k, prelim_2026, specials, pools)
                                            for k in prelim_2026}}
        cand = detail["candidate"]
        cand["prelim_winner"], cand["prelim_second"] = winner(cand["prelim_2026"])
        cand["winner"], cand["second"] = winner(cand["final"])
        winners_prelim[elec_id], winners_final[elec_id] = cand["prelim_winner"], cand["winner"]
        details[elec_id] = detail
    for elec_id in omitted:  # held at the preliminary winner
        p1, _ = winner(data[("2026", "prelim", "candidate")][elec_id])
        winners_prelim[elec_id] = winners_final[elec_id] = p1

    return {"base": base, "files": input_files, "omitted_base": omitted_base,
            "names": names, "data": data, "categories": categories, "elec_names": elec_names,
            "labels": labels, "sources": sources, "pools": pools_national, "scales": scales,
            "national_ratios": national_ratios, "revision_ratio": revision_ratio,
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
    parser.add_argument("--base", choices=sorted(OMITTED), default=DEFAULT_BASE)
    parser.add_argument("--outdir", default="results/projection-2026")
    args = parser.parse_args()
    base = args.base

    c = compute(base)
    names, labels, data, elec_names = c["names"], c["labels"], c["data"], c["elec_names"]
    omitted, scales, pools_national = c["omitted"], c["scales"], c["pools"]
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
    header = ["elec_id", "elec_name", "party_id", "name", "party_id_" + base, "prelim_votes", "multiplier",
              "projected_special_votes", "projected_final_votes", "projected_final_pct"]
    for filename, rows in [("electorates_party.csv", party_rows), ("electorates_candidate.csv", candidate_rows)]:
        with open(os.path.join(args.outdir, output_name(filename, base)), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    summary.sort(key=lambda s: s["projected_margin_pct"])
    with open(os.path.join(args.outdir, output_name("electorates_summary.csv", base)), "w", newline="",
              encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        for s in summary:
            # Votes to whole numbers; shares as percentages to 4 decimals, as in the other files.
            writer.writerow(dict(s, **{k: "{0:.0f}".format(s[k]) for k in ["projected_margin", "projected_specials"]},
                                 **{k: "{0:.4f}".format(100 * s[k]) for k in
                                    ["omitted_share", "prelim_margin_pct", "projected_margin_pct"]}))

    # Report
    for pool in SPECIAL_POOLS:
        projected = sum(d["party"]["pools"][pool]["volume"] for d in c["electorates"].values()) + sum(
            sum(data[("2026", "prelim", "party")][e].values()) * c["national_ratios"][pool] * scales[pool]
            for e in omitted)
        print("{0}: scale factor {1:.4f}, projected party votes {2:,.0f} (national projection {3:,.0f})".format(
            pool, scales[pool], projected, pools_national[pool]["volume"]))
    print("revisions: {0:.4%} of the preliminary count".format(c["revision_ratio"]))
    print("projected special candidate votes {0:,.0f}".format(sum(float(r[7]) for r in candidate_rows)))
    print("not projected (all {0} sources omitted): ".format(base) + ", ".join(elec_names["2026"][e] for e in omitted))
    partly = [(s["name"], s["omitted_share"]) for s in summary if s["omitted_share"] > 0]
    if partly:
        print("partly from omitted {0} electorates: ".format(base) +
              ", ".join("{0} ({1:.1%})".format(*p) for p in partly))
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
        print("candidates over {0:.0%} with no {1} candidate counterpart (multiplier 1 unless shown):".format(
            NOTABLE_SHARE, base))
        for n, c in notable:
            print("  {0}: {1}".format(n, c))

    # Step 5: seats
    with open(ps.default_output(base), newline="", encoding="utf-8") as f:
        party_votes = {row["party_id"]: float(row["projected_final_votes"]) for row in csv.DictReader(f)}
    print()
    for label, won in [("preliminary electorates", winners_prelim), ("projected electorates", winners_final)]:
        seats, other = seats_from(party_votes, won)
        house = sum(s[2] for s in seats.values()) + other
        print("projected party vote, {0}: {1} seats (overhang {2}, majority {3}): {4}".format(
            label, house, house - TOTAL_SEATS, house // 2 + 1, ", ".join(
                "{0} {1}".format(names.short_names[p], s[2]) for p, s in
                sorted(seats.items(), key=lambda x: -x[1][2]) if s[2])))
    print("wrote {0} in {1}".format(", ".join(output_name(f, base) for f in (
        "electorates_party.csv", "electorates_candidate.csv", "electorates_summary.csv")), args.outdir))


if __name__ == "__main__":
    main()
