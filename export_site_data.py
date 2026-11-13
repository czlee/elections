"""Exports the 2026 projection, with its intermediate numbers, as JSON for the
visualisation site (site/). Runs project_specials.compute() and
project_electorates.compute(), so it needs the same inputs, and
results/projection-2026/*.csv to check against (run both scripts first).

Writes, in site/src/lib/data/<base>/:
  national.json     the national projection, Sainte-Laguë ladders and seats
  electorates.json  one entry per 2026 electorate: candidate and party votes
                    at every step, its 2023 sources and the break-even
                    multiplier for the projected runner-up

Only the 2023 base is implemented so far.
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
PRELIM_2023_STATS = "results/2023-prelim/electorate_stats.csv"

# Links to the raw data, for the site to cite. The results website's HTML
# pages are blocked to scripts (NOTES.md), so the page links haven't been
# fetched; the XML links are the files download.py reads.
RESULTS = "https://www.electionresults.govt.nz/"
WAYBACK = "https://web.archive.org/web/{0}/" + RESULTS + "{1}"
NATIONAL_SOURCES = {
    "release_2026": {"label": "Electoral Commission, 2026 preliminary results press release",
                     "url": "https://elections.nz/media-and-news/2026/2026-general-election-preliminary-results"},
    "release_2023": {"label": "Electoral Commission, 2023 election night press release (Wayback Machine)",
                     "url": "https://web.archive.org/web/20231021094025/https://elections.nz/media-and-news/2023/"
                            "election-night-results-for-the-2023-general-election"},
    "prelim_2023": {"label": "2023 preliminary count, overview page (Wayback Machine, 26 Oct 2023)",
                    "url": WAYBACK.format("20231026013849", "electionresults_2023_preliminary/index.html")},
    "final_2023": {"label": "2023 official results", "url": RESULTS + "electionresults_2023/",
                   "xml": RESULTS + "electionresults_2023/xml/election.xml"},
    "prelim_2026": {"label": "2026 preliminary count", "url": RESULTS + "electionresults_2026_preliminary/",
                    "xml": RESULTS + "electionresults_2026_preliminary/xml/election.xml"},
}


def electorate_links_2026(elec_id):
    return {"prelim_2026": {"url": RESULTS + "electionresults_2026_preliminary/electorate-details-{0:02d}.html".format(elec_id),
                            "xml": RESULTS + "electionresults_2026_preliminary/xml/e{0:02d}/e{0:02d}.xml".format(elec_id)}}


def electorate_links_2023(elec_id, timestamps):
    links = {"final_2023": {"url": RESULTS + "electionresults_2023/electorate-details-{0:02d}.html".format(elec_id),
                            "xml": RESULTS + "electionresults_2023/xml/e{0:02d}/e{0:02d}.xml".format(elec_id)}}
    if elec_id in timestamps:
        links["prelim_2023"] = {"url": WAYBACK.format(
            timestamps[elec_id], "electionresults_2023_preliminary/electorate-details-{0:02d}.html".format(elec_id))}
    return links


def read_timestamps():
    with open(PRELIM_2023_STATS, newline="", encoding="utf-8") as f:
        return {int(r["elec_id"]): r["wayback_timestamp"] for r in csv.DictReader(f)}


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def seats_json(seats, party_votes):
    return {p: {"electorate": e, "list": l, "total": t} for p, (e, l, t) in seats.items()
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


def read_roll():
    roll = {}
    with open(pe.CONCORDANCE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            roll[int(row["elec_id_2026"])] = row["roll"]
    return roll


def national(cn, ce):
    names = cn["names"]
    final_2026 = cn["final_2026"]
    # Seats as the site shows them: preliminary votes with preliminary
    # electorate winners, and projected votes with projected winners.
    prelim_seats, prelim_other = pe.seats_from(cn["prelim_2026"], ce["winners_prelim"])
    final_seats, final_other = pe.seats_from(final_2026, ce["winners_final"])
    assert prelim_seats == cn["prelim_seats"]
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
    for p in sorted(cn["final_2023"], key=lambda p: -cn["final_2023"][p]):
        base_parties.append({
            "id": p, "short": names.short_names[p], "prelim": cn["prelim_2023"][p], "final": cn["final_2023"][p],
            "specials": cn["specials_2023"][p], "prelim_share": cn["prelim_share_2023"][p],
            "special_share": cn["special_share_2023"][p], "multiplier": cn["multipliers_2023"][p],
        })
    house = {k: sum(s[2] for s in seats.values()) + other
             for k, seats, other in [("prelim", prelim_seats, prelim_other), ("projected", final_seats, final_other)]}
    return {
        "base": "2023", "generated": date.today().isoformat(),
        "estimate_base": cn["estimate_2023"], "estimate_2026": cn["estimate_2026"],
        "adjustment": cn["adjustment"], "projected_specials": cn["projected_specials_total"],
        "base_totals": {"prelim": sum(cn["prelim_2023"].values()), "final": sum(cn["final_2023"].values()),
                        "specials": sum(cn["specials_2023"].values())},
        "prelim_total": sum(cn["prelim_2026"].values()), "final_total": sum(final_2026.values()),
        "parties": parties, "base_parties": base_parties,
        "seats": {"prelim": seats_json(prelim_seats, final_2026), "projected": seats_json(final_seats, final_2026)},
        "other_electorates": {"prelim": prelim_other, "projected": final_other},
        "house": house, "list_pool": TOTAL_SEATS, "entitlement": entitlement,
        "sources": NATIONAL_SOURCES,
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
    for key in sorted(set(prelim_n) | set(final_n), key=lambda k: -final_n.get(k, 0)):
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
    roll = read_roll()
    # Candidate names by (elec_id, key), for "who was the 2023 counterpart"
    names_2023 = candidate_names(pe.FILES[("2023", "final", "candidate")], "2023", ce["names"])
    ce["names_2026"] = candidate_names(pe.FILES[("2026", "prelim", "candidate")], "2026", ce["names"])
    data, en23 = ce["data"], ce["elec_names"]["2023"]
    timestamps = read_timestamps()

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
            src = {"id": e23, "name": en23[e23], "share_of_2023": share_of_2023, "share_of_2026": share_of_2026,
                   "omitted": e23 in pe.OMITTED_2023, "links": electorate_links_2023(e23, timestamps)}
            if not src["omitted"]:
                for kind in ["party", "candidate"]:
                    p, f = data[("2023", "prelim", kind)][e23], data[("2023", "final", kind)][e23]
                    src[kind] = {"prelim": sum(p.values()), "final": sum(f.values()),
                                 "by_key": {key_id(k): [p.get(k, 0), f.get(k, 0)] for k in set(p) | set(f)}}
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
    assert nat["house"]["projected"] == nat["house"]["prelim"] == 131, nat["house"]
    with open(os.path.join(CSV_DIR, "national.csv"), newline="", encoding="utf-8") as f:
        csv_nat = {r["party_id"]: r for r in csv.DictReader(f)}
    for p in nat["parties"]:
        assert "{0:.0f}".format(p["final"]) == csv_nat[p["id"]]["projected_final_votes"], p["id"]
        assert nat["seats"]["projected"][p["id"]]["total"] == int(csv_nat[p["id"]]["projected_seats"]), p["id"]
    with open(os.path.join(CSV_DIR, "electorates_summary.csv"), newline="", encoding="utf-8") as f:
        csv_sum = {int(r["elec_id"]): r for r in csv.DictReader(f)}
    with open(os.path.join(CSV_DIR, "electorates_candidate.csv"), newline="", encoding="utf-8") as f:
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
    assert flips == ["Wellington Bays"], flips
    assert len({e["slug"] for e in elecs}) == len(elecs) == 71


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outdir", default=OUTDIR)
    args = parser.parse_args()

    cn, ce = ps.compute(), pe.compute()
    nat, elecs = national(cn, ce), electorates(ce)
    check(nat, elecs)
    outdir = os.path.join(args.outdir, nat["base"])
    os.makedirs(outdir, exist_ok=True)
    for filename, obj in [("national.json", nat), ("electorates.json", elecs)]:
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
