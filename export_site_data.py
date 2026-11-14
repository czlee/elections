"""Exports the 2026 projection, with its intermediate numbers, as JSON for the
visualisation site (site/). Runs project_specials.compute() and, for a base
with electorate projections, project_electorates.compute(), so it needs the
same inputs, and results/projection-2026/*.csv to check against (run the
scripts first, with the same --base).

Writes, in site/src/lib/data/<base>/:
  national.json     the national projection, Sainte-Laguë ladders and seats
  electorates.json  one entry per 2026 electorate: candidate and party votes
                    at every step, its base-year sources and the break-even
                    multiplier for the projected runner-up (only for bases
                    in ELECTORATE_BASES)

2017 and 2023 have electorate projections. For the other base (2020), both
counts' seats hold electorates at the 2026 preliminary winners, as
project_specials.py does.
"""
import argparse
import csv
import json
import os
import re
import unicodedata
from datetime import date

import project_electorates as pe
import project_specials as ps
from seats import TOTAL_SEATS, allocate, quotient_ladder

OUTDIR = "site/src/lib/data"
CSV_DIR = "results/projection-2026"
LADDER_BEFORE, LADDER_AFTER = 12, 8

# Links to the raw data, for the site to cite. The results website's HTML
# pages are blocked to scripts (NOTES.md), so the page links haven't been
# fetched; the XML links are the files download.py reads.
RESULTS = "https://www.electionresults.govt.nz/"
WAYBACK = "https://web.archive.org/web/{0}/" + RESULTS + "{1}"
RELEASES = "https://elections.nz/media-and-news/"
ELECTORATE_BASES = {"2017", "2023"}
# Regression guards for check(): ((preliminary House, projected House), flips).
EXPECTED = {
    "2017": ((131, 130), ["Hamilton East", "Wairarapa", "Wellington Bays"]),
    "2023": ((131, 131), ["Wellington Bays"]),
}
SOURCES_2026 = {
    "release_2026": {"label": "Electoral Commission, 2026 preliminary results press release",
                     "url": RELEASES + "2026/2026-general-election-preliminary-results"},
    "prelim_2026": {"label": "2026 preliminary count", "url": RESULTS + "electionresults_2026_preliminary/",
                    "xml": RESULTS + "electionresults_2026_preliminary/xml/election.xml"},
}
# The base election's press release and preliminary count. The 2017 and 2020
# releases are blocked to scripts (the user saved copies, NOTES.md); 2023's
# is read via the Wayback Machine.
BASE_SOURCES = {
    "2017": {
        "release_base": {"label": "Electoral Commission, 2017 preliminary results press release",
                         "url": RELEASES + "2017/preliminary-results-for-the-2017-general-election"},
        "prelim_base": {"label": "2017 preliminary count, overview page (Wayback Machine, 11 Oct 2017)",
                        "url": WAYBACK.format("20171011234809", "electionresults_2017_preliminary/index.html")},
    },
    "2020": {
        "release_base": {"label": "Electoral Commission, 2020 election night press release",
                         "url": RELEASES + "2020/preliminary-results-for-the-2020-general-election"},
        "prelim_base": {"label": "2020 preliminary count, overview page (Wayback Machine, 3 Nov 2020)",
                        "url": WAYBACK.format("20201103192629", "electionresults_2020_preliminary/index.html")},
    },
    "2023": {
        "release_base": {"label": "Electoral Commission, 2023 election night press release (Wayback Machine)",
                         "url": "https://web.archive.org/web/20231021094025/" + RELEASES + "2023/"
                                "election-night-results-for-the-2023-general-election"},
        "prelim_base": {"label": "2023 preliminary count, overview page (Wayback Machine, 26 Oct 2023)",
                        "url": WAYBACK.format("20231026013849", "electionresults_2023_preliminary/index.html")},
    },
}


def national_sources(base):
    final = {"label": "{0} official results".format(base), "url": RESULTS + "electionresults_{0}/".format(base),
             "xml": RESULTS + "electionresults_{0}/xml/election.xml".format(base)}
    return dict(SOURCES_2026, final_base=final, **BASE_SOURCES[base])


def electorate_links_2026(elec_id):
    return {"prelim_2026": {"url": RESULTS + "electionresults_2026_preliminary/electorate-details-{0:02d}.html".format(elec_id),
                            "xml": RESULTS + "electionresults_2026_preliminary/xml/e{0:02d}/e{0:02d}.xml".format(elec_id)}}


def electorate_links_base(base, elec_id, timestamps):
    links = {"final_base": {
        "url": RESULTS + "electionresults_{0}/electorate-details-{1:02d}.html".format(base, elec_id),
        "xml": RESULTS + "electionresults_{0}/xml/e{1:02d}/e{1:02d}.xml".format(base, elec_id)}}
    if elec_id in timestamps:
        links["prelim_base"] = {"url": WAYBACK.format(
            timestamps[elec_id], "electionresults_{0}_preliminary/electorate-details-{1:02d}.html".format(
                base, elec_id))}
    return links


def read_timestamps(base):
    """{elec_id: Wayback timestamp} of the scraped base-year preliminary pages."""
    with open("results/{0}-prelim/electorate_stats.csv".format(base), newline="", encoding="utf-8") as f:
        return {int(r["elec_id"]): r["wayback_timestamp"] for r in csv.DictReader(f)}


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def seats_json(seats, party_votes):
    # Most seats first, then by party_id, so the order doesn't depend on set
    # iteration order in seats.py.
    return {p: {"electorate": e, "list": l, "total": t}
            for p, (e, l, t) in sorted(seats.items(), key=lambda x: (-x[1][2], x[0]))
            if t > 0 or p in party_votes}


def breakeven(prelim, multipliers, volume, a, b):
    """The multiplier that `b` would need, all else equal, to tie with `a`
    after specials. Specials are shared as volume * s_k m_k / sum(s_j m_j),
    where s is the 2026 preliminary share, so the tie condition is linear in
    m_b. Returns None if no multiplier would do it."""
    total = sum(prelim.values())
    s = {k: v / total for k, v in prelim.items()}
    d = prelim[a] - prelim[b]
    rest = sum(s[k] * multipliers[k] for k in prelim if k != b)
    if volume <= d:
        return None  # b can't catch up even with every special vote
    return (d * rest + volume * s[a] * multipliers[a]) / (s[b] * (volume - d))


def check_breakeven(prelim, multipliers, volume, a, b, m_b):
    m = dict(multipliers, **{b: m_b})
    norm = sum(prelim[k] * m[k] for k in prelim)
    fa = prelim[a] + volume * prelim[a] * m[a] / norm
    fb = prelim[b] + volume * prelim[b] * m[b] / norm
    assert abs(fa - fb) < 1e-6 * volume, (a, b, fa, fb)


def key_id(key):
    """JSON-friendly key: party_id, or "other:<candidate>"."""
    return "other:" + key[1] if isinstance(key, tuple) else key


def read_roll(base):
    roll = {}
    with open(pe.concordance_file(base), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            roll[int(row["elec_id_2026"])] = row["roll"]
    return roll


def national(cn, ce=None):
    """`ce` is project_electorates.compute()'s output, or None for a base
    without electorate projections."""
    names, base = cn["names"], cn["base"]
    final_2026 = cn["final_2026"]
    if ce:
        # Seats as the site shows them: preliminary votes with preliminary
        # electorate winners, and projected votes with projected winners.
        prelim_seats, prelim_other = pe.seats_from(cn["prelim_2026"], ce["winners_prelim"])
        final_seats, final_other = pe.seats_from(final_2026, ce["winners_final"])
        assert prelim_seats == cn["prelim_seats"]
    else:
        # Electorates held at the preliminary winners in both counts.
        prelim_seats, final_seats = cn["prelim_seats"], cn["final_seats"]
        prelim_other = final_other = cn["other_electorates"]
    prelim_ladder, n_prelim = quotient_ladder(cn["prelim_2026"], {p: s[0] for p, s in prelim_seats.items()},
                                              prelim_other, LADDER_BEFORE, LADDER_AFTER)
    final_ladder, n_final = quotient_ladder(final_2026, {p: s[0] for p, s in final_seats.items()},
                                            final_other, LADDER_BEFORE, LADDER_AFTER)
    entitlement = {}
    for key, votes, seats, other in [("prelim", cn["prelim_2026"], prelim_seats, prelim_other),
                                     ("projected", final_2026, final_seats, final_other)]:
        full, n = quotient_ladder(votes, {p: s[0] for p, s in seats.items()}, other, TOTAL_SEATS, 0)
        entitlement[key] = {}
        for r in full:
            entitlement[key][r["party"]] = entitlement[key].get(r["party"], 0) + 1
        assert sum(entitlement[key].values()) == n
    for ladder in (prelim_ladder, final_ladder):
        for r in ladder:
            r["quotient"] = round(r["quotient"], 1)

    parties = []
    for p in sorted(cn["prelim_2026"], key=lambda p: -final_2026[p]):
        link = cn["links"][p]
        parties.append({
            "id": p, "short": names.short_names[p], "name": cn["display_names"][p].strip(), "link": link,
            "prelim": cn["prelim_2026"][p], "prelim_share": cn["prelim_share_2026"][p],
            "multiplier": cn["multipliers"][p], "special_share": cn["special_share_2026"][p],
            "specials": cn["specials_2026"][p], "final": final_2026[p],
            "final_share": final_2026[p] / sum(final_2026.values()),
        })
    base_parties = []
    for p in sorted(cn["final_base"], key=lambda p: -cn["final_base"][p]):
        base_parties.append({
            "id": p, "short": names.short_names[p], "prelim": cn["prelim_base"][p], "final": cn["final_base"][p],
            "specials": cn["specials_base"][p], "prelim_share": cn["prelim_share_base"][p],
            "special_share": cn["special_share_base"][p], "multiplier": cn["multipliers_base"][p],
        })
    house = {k: sum(s[2] for s in seats.values()) + other
             for k, seats, other in [("prelim", prelim_seats, prelim_other), ("projected", final_seats, final_other)]}
    return {
        "base": base, "has_electorates": ce is not None, "generated": date.today().isoformat(),
        "estimate_base": cn["estimate_base"], "estimate_2026": cn["estimate_2026"],
        "adjustment": cn["adjustment"], "projected_specials": cn["projected_specials_total"],
        "base_totals": {"prelim": sum(cn["prelim_base"].values()), "final": sum(cn["final_base"].values()),
                        "specials": sum(cn["specials_base"].values())},
        "prelim_total": sum(cn["prelim_2026"].values()), "final_total": sum(final_2026.values()),
        "parties": parties, "base_parties": base_parties,
        "seats": {"prelim": seats_json(prelim_seats, final_2026), "projected": seats_json(final_seats, final_2026)},
        "other_electorates": {"prelim": prelim_other, "projected": final_other},
        "house": house, "list_pool": TOTAL_SEATS, "entitlement": entitlement,
        "sources": national_sources(base),
        "ladder": {"prelim": prelim_ladder, "projected": final_ladder,
                   "allocated": {"prelim": n_prelim, "projected": n_final}},
    }


def candidate_names(filename, election, names):
    """{(elec_id, key): candidate name}, with keys as in project_electorates.read_votes.
    Read from the CSV columns, because names and party names can contain
    parentheses, so labels like "NAME (Party)" can't be split reliably."""
    out = {}
    with open(filename, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = names.ids.get((election, row["party"]), ("other", row["candidate"]))
            out[(int(row["elec_id"]), key)] = row["candidate"]
    return out


def rows_for(kind, elec_id, d, ce, names_2023):
    """One row per 2026 key, with every step of the projection."""
    names, labels = ce["names"], ce["labels"]
    prelim, final = d["prelim_2026"], d["final"]
    total_prelim, total_final = sum(prelim.values()), sum(final.values())
    n_prelim_total = sum(d["prelim_n"].values())
    n_specials_total = sum(d["final_n"].values()) - n_prelim_total
    rows = []
    for key in sorted(prelim, key=lambda k: -final[k]):
        link = d["links"][key]
        row = {"key": key_id(key), "party": None if isinstance(key, tuple) else key,
               "party_short": None if isinstance(key, tuple) else names.short_names[key],
               "link": link, "prelim": prelim[key], "prelim_share": prelim[key] / total_prelim,
               "multiplier": d["multipliers"][key], "specials": d["specials"][key],
               "special_share": d["specials"][key] / d["volume"],
               "final": final[key], "final_share": final[key] / total_final}
        if kind == "candidate":
            row["candidate"] = ce["names_2026"][(elec_id, key)]
            row["label"] = labels[(elec_id, key)]
        else:
            row["label"] = names.short_names[key]
        if link and link != "party vote":
            np_, nf = d["prelim_n"][link], d["final_n"].get(link, 0)
            row["base"] = {"key": link, "prelim": np_, "final": nf, "specials": nf - np_,
                           "prelim_share": np_ / n_prelim_total, "special_share": (nf - np_) / n_specials_total}
            if kind == "candidate":
                row["base"]["candidates"] = sorted(
                    {names_2023[(e, link)] for e, _, _ in ce["electorates"][elec_id]["live"]
                     if (e, link) in names_2023})
        rows.append(row)
    return rows


def base_rows(kind, elec_id, d, ce, names_2023):
    """The notional base-year count for every key in the area (including ones
    with no 2026 counterpart), with each key's multiplier."""
    names = ce["names"]
    prelim_n, final_n = d["prelim_n"], d["final_n"]
    total_p = sum(prelim_n.values())
    total_s = sum(final_n.values()) - total_p
    live = ce["electorates"][elec_id]["live"]
    rows = []
    # Ties broken by key, so the order doesn't depend on set iteration order.
    for key in sorted(set(prelim_n) | set(final_n), key=lambda k: (-final_n.get(k, 0), key_id(k))):
        p, f = prelim_n.get(key, 0), final_n.get(key, 0)
        row = {"key": key_id(key), "party": None if isinstance(key, tuple) else key,
               "label": key[1] if isinstance(key, tuple) else names.short_names[key],
               "prelim": p, "final": f, "specials": f - p,
               "prelim_share": p / total_p, "special_share": (f - p) / total_s,
               "multiplier": ((f - p) / total_s) / (p / total_p) if p > 0 else None}
        if kind == "candidate" and not isinstance(key, tuple):
            # Each 2023 candidate of this party in the area, with the share of the
            # 2026 electorate's population their electorate contributes.
            row["candidates"] = sorted(
                ({"name": names_2023[(e, key)], "share": share_2026} for e, _, share_2026 in live
                 if (e, key) in names_2023), key=lambda c: -c["share"])
        rows.append(row)
    return {"rows": rows, "prelim": total_p, "final": sum(final_n.values()), "specials": total_s}


def electorates(ce):
    roll = read_roll(ce["base"])
    base = ce["base"]
    # Candidate names by (elec_id, key), for "who was the base-year counterpart"
    names_2023 = candidate_names(ce["files"][(base, "final", "candidate")], base, ce["names"])
    ce["names_2026"] = candidate_names(pe.FILES[("2026", "prelim", "candidate")], "2026", ce["names"])
    data, en23 = ce["data"], ce["elec_names"][base]
    timestamps = read_timestamps(base)

    out = []
    for elec_id in sorted(ce["sources"]):
        name = ce["elec_names"]["2026"][elec_id]
        entry = {"id": elec_id, "name": name, "slug": slugify(name), "roll": roll[elec_id],
                 "links": electorate_links_2026(elec_id)}
        if elec_id in ce["omitted"]:
            prelim = data[("2026", "prelim", "candidate")][elec_id]
            w = ce["winners_prelim"][elec_id]
            entry.update({"omitted": True, "winner_label": ce["labels"][(elec_id, w)],
                          "winner_party": None if isinstance(w, tuple) else w,
                          "candidate": {"rows": [{"key": key_id(k), "label": ce["labels"][(elec_id, k)],
                                                  "party": None if isinstance(k, tuple) else k,
                                                  "prelim": v} for k, v in
                                                 sorted(prelim.items(), key=lambda x: -x[1])]}})
            out.append(entry)
            continue
        detail = ce["electorates"][elec_id]
        entry["omitted"] = False
        entry["omitted_share"] = detail["omitted_share"]
        entry["sources"] = []
        for e23, share_of_2023, share_of_2026 in ce["sources"][elec_id]:
            src = {"id": e23, "name": en23[e23], "share_of_base": share_of_2023, "share_of_2026": share_of_2026,
                   "omitted": e23 in ce["omitted_base"], "links": electorate_links_base(base, e23, timestamps)}
            if not src["omitted"]:
                for kind in ["party", "candidate"]:
                    p, f = data[(base, "prelim", kind)][e23], data[(base, "final", kind)][e23]
                    src[kind] = {"prelim": sum(p.values()), "final": sum(f.values()),
                                 "by_key": {key_id(k): [p.get(k, 0), f.get(k, 0)]
                                            for k in sorted(set(p) | set(f), key=key_id)}}
            entry["sources"].append(src)
        for kind in ["party", "candidate"]:
            d = detail[kind]
            entry[kind] = {"ratio": d["ratio"], "volume": d["volume"], "scale": ce["scale"],
                           "prelim_total": sum(d["prelim_2026"].values()),
                           "base_rows": base_rows(kind, elec_id, d, ce, names_2023),
                           "rows": rows_for(kind, elec_id, d, ce, names_2023)}
        d = detail["candidate"]
        a, b = d["winner"], d["second"]
        pa, pb = d["prelim_winner"], d["prelim_second"]
        m_b = breakeven(d["prelim_2026"], d["multipliers"], d["volume"], a, b)
        if m_b is not None:
            check_breakeven(d["prelim_2026"], d["multipliers"], d["volume"], a, b, m_b)
        entry.update({
            "flips": pa != a,
            "prelim_winner": key_id(pa), "prelim_second": key_id(pb),
            "winner": key_id(a), "second": key_id(b),
            "prelim_margin": d["prelim_2026"][pa] - d["prelim_2026"][pb],
            "prelim_margin_pct": (d["prelim_2026"][pa] - d["prelim_2026"][pb]) / sum(d["prelim_2026"].values()),
            "margin": d["final"][a] - d["final"][b],
            "margin_pct": (d["final"][a] - d["final"][b]) / sum(d["final"].values()),
            # The projected runner-up's margin bridge: preliminary lead of the
            # projected winner over the projected runner-up, then each one's specials.
            "bridge": {"prelim_lead": d["prelim_2026"][a] - d["prelim_2026"][b],
                       "specials_winner": d["specials"][a], "specials_second": d["specials"][b]},
            "breakeven": {"key": key_id(b), "needed": m_b, "had": d["multipliers"][b],
                          "winner_multiplier": d["multipliers"][a]},
        })
        out.append(entry)
    return out


def check(nat, elecs):
    """Checks the export against the CSVs written by the projection scripts."""
    with open(ps.default_output(nat["base"]), newline="", encoding="utf-8") as f:
        csv_nat = {r["party_id"]: r for r in csv.DictReader(f)}
    base = nat["base"]
    for p in nat["parties"]:
        assert "{0:.0f}".format(p["final"]) == csv_nat[p["id"]]["projected_final_votes"], p["id"]
        if elecs is None:
            # The CSV's seats hold electorates at the preliminary winners, as
            # the export does without electorate projections.
            assert nat["seats"]["projected"][p["id"]]["total"] == int(csv_nat[p["id"]]["projected_seats"]), p["id"]
    if elecs is None:
        return
    house, expected_flips = EXPECTED[base]
    assert (nat["house"]["prelim"], nat["house"]["projected"]) == house, nat["house"]
    with open(os.path.join(CSV_DIR, pe.output_name("electorates_summary.csv", base)), newline="",
              encoding="utf-8") as f:
        csv_sum = {int(r["elec_id"]): r for r in csv.DictReader(f)}
    with open(os.path.join(CSV_DIR, pe.output_name("electorates_candidate.csv", base)), newline="",
              encoding="utf-8") as f:
        csv_cand = {}
        for r in csv.DictReader(f):
            csv_cand[(int(r["elec_id"]), r["name"])] = r
    for e in elecs:
        if e["omitted"]:
            assert e["id"] not in csv_sum
            continue
        s = csv_sum[e["id"]]
        assert "{0:.0f}".format(e["margin"]) == s["projected_margin"], e["name"]
        assert e["prelim_margin"] == int(s["prelim_margin"]), e["name"]
        assert str(e["flips"]) == s["flips"], e["name"]
        for r in e["candidate"]["rows"]:
            assert "{0:.0f}".format(r["final"]) == csv_cand[(e["id"], r["label"])]["projected_final_votes"]
    flips = [e["name"] for e in elecs if e.get("flips")]
    assert flips == expected_flips, flips
    assert len({e["slug"] for e in elecs}) == len(elecs) == 71


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", choices=sorted(ps.BASES), default=ps.DEFAULT_BASE)
    parser.add_argument("--outdir", default=OUTDIR)
    args = parser.parse_args()

    cn = ps.compute(args.base)
    if args.base in ELECTORATE_BASES:
        ce = pe.compute(args.base)
        nat, elecs = national(cn, ce), electorates(ce)
    else:
        nat, elecs = national(cn), None
    check(nat, elecs)
    outdir = os.path.join(args.outdir, nat["base"])
    os.makedirs(outdir, exist_ok=True)
    outputs = [("national.json", nat)] + ([("electorates.json", elecs)] if elecs is not None else [])
    for filename, obj in outputs:
        path = os.path.join(outdir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(compact(obj), f, ensure_ascii=False, separators=(",", ":"))
        print("wrote {0} ({1:,} bytes)".format(path, os.path.getsize(path)))


def compact(obj):
    """Rounds floats for a smaller file: shares and multipliers (under 10) to
    6 decimal places, vote counts to 2."""
    if isinstance(obj, float):
        return round(obj, 6 if abs(obj) < 10 else 2)
    if isinstance(obj, dict):
        return {k: compact(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [compact(v) for v in obj]
    return obj


if __name__ == "__main__":
    main()
