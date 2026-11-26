"""Exports the "no Māori electorates" analysis (maori_to_general.py) as JSON for
the site in maori-site/, in maori-site/src/lib/data/:

  national.json     seats as counted and with no Māori electorates, the
                    Sainte-Laguë entitlements, where the Māori-roll votes went
                    and a sensitivity table for the share of Te Pāti Māori
                    votes that go to Labour
  electorates.json  the 64 general electorates: candidates' preliminary
                    votes, the Māori-roll votes added to each, the new
                    result and the Labour break-even

Run maori_to_general.py's inputs first (download.py, download_maori_places.py).
The JSON is committed, since CI can't regenerate it.
"""
import csv
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict

import maori_to_general as m
from parties import PartyNames
from seats import TOTAL_SEATS, _quotients, allocate

OUTDIR = "maori-site/src/lib/data"
SHARES = [0, 0.25, 0.5, 0.75, 1]
RESULTS = "https://www.electionresults.govt.nz/"
LABOUR, TPM = "Labour Party", "Te Pāti Māori"


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def read_rows():
    """Returns ({e_no: name}, {e_no: [(candidate, party, votes)]}) for every
    electorate, Māori and general."""
    names, rows = {}, defaultdict(list)
    with open(os.path.join(m.PRELIM, "candidate_votes.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            e = int(r["elec_id"])
            names[e] = r["elec_name"]
            rows[e].append((r["candidate"], r["party"], int(r["votes"])))
    return names, rows


def winner_of(votes):
    ranked = sorted(votes.items(), key=lambda x: -x[1])
    return ranked[0][0]


def main():
    pn = PartyNames()
    unlisted = {}  # parties in the 2026 data that party_names.toml doesn't know (small ones)

    def pid(party):
        if party == m.INDEPENDENT:
            return None
        try:
            return pn.party_id("2026", party)
        except KeyError:
            unlisted[slugify(party)] = party.strip()
            return slugify(party)
    c_party = m.read_candidates()
    gnames, general = m.read_general()
    places = m.read_places(c_party)
    m.check_totals(places)
    names, rows = read_rows()
    maori_names = {e: names[e] for e in m.MAORI}

    new, log, detail = m.project(general, places)
    by_share = {s: m.project(general, places, s)[0] for s in SHARES}

    # Seats.
    party_votes = Counter()
    with open(os.path.join(m.PRELIM, "party_votes.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            party_votes[r["party"]] += int(r["votes"])
    all_votes = {e: {} for e in rows}
    for e, rs in rows.items():
        for _, party, v in rs:
            all_votes[e][party] = all_votes[e].get(party, 0) + v
    counted_won = Counter(winner_of(v) for v in all_votes.values())
    none_won = Counter(winner_of(v) for v in new.values())

    def seats(won):
        eligible = {p: n for p, n in won.items() if p in party_votes}
        other = sum(n for p, n in won.items() if p not in party_votes)
        res = allocate(party_votes, eligible, other)
        _, to_allocate, quotients = _quotients(party_votes, eligible, other, TOTAL_SEATS, 0.05)
        ent = Counter(p for _, p, _ in quotients[:to_allocate])
        out = {pid(p): {"electorate": e, "list": l, "total": t}
               for p, (e, l, t) in sorted(res.items(), key=lambda x: (-x[1][2], x[0])) if t > 0}
        other_out = {"electorate": other, "list": 0, "total": other}
        return out, {pid(p): n for p, n in ent.items()}, sum(r[2] for r in res.values()) + other, other_out

    seats_c, ent_c, house_c, other_c = seats(counted_won)
    seats_n, ent_n, house_n, other_n = seats(none_won)
    assert other_c["total"] == 0 and other_n["total"] == 0, "independents won electorates; handle them"
    total_party = sum(party_votes.values())

    # Electorates.
    electorates, flips = [], []
    for e in sorted(gnames):
        prelim = general[e]
        w0 = winner_of(prelim)
        votes_new = new[e]
        w1 = winner_of(votes_new)
        # Labour break-even on the share of Te Pāti Māori votes going to Labour.
        l0 = by_share[0][e][LABOUR]
        t = by_share[1][e][LABOUR] - l0
        rival = max(v for p, v in votes_new.items() if p != LABOUR)
        breakeven = (rival - l0) / t if t > 0 else None
        cands = []
        for cand, party, v in rows[e]:
            added = votes_new.get(party, 0) - prelim.get(party, 0) if party != m.INDEPENDENT else 0
            cands.append({"candidate": cand, "party": pid(party), "prelim": v, "added": added, "total": v + added})
        cands.sort(key=lambda c: -c["total"])
        added_rows = [
            {"from": maori_names[mo], "from_slug": slugify(maori_names[mo]), "party": pid(party), "how": how,
             "to": pid(target) if target else None, "votes": n}
            for (home, mo, party, how, target), n in sorted(detail.items(), key=lambda x: (x[0][1], -x[1]))
            if home == e and n > 0]
        top_prelim = sorted(prelim.items(), key=lambda x: -x[1])
        second_prelim = top_prelim[1]
        top_new = sorted(votes_new.items(), key=lambda x: -x[1])
        entry = {
            "id": e, "name": gnames[e], "slug": slugify(gnames[e]),
            "candidates": cands, "added_rows": added_rows,
            "added_total": sum(r["votes"] for r in added_rows),
            "maori_votes": sum(r["votes"] for r in added_rows),
            "winner_prelim": pid(w0), "winner_new": pid(w1), "flips": w0 != w1,
            "margin_prelim": top_prelim[0][1] - second_prelim[1],
            "margin_new": top_new[0][1] - top_new[1][1],
            "margin_prelim_pct": (top_prelim[0][1] - second_prelim[1]) / sum(prelim.values()),
            "margin_new_pct": (top_new[0][1] - top_new[1][1]) / sum(votes_new.values()),
            "runner_up_prelim": pid(second_prelim[0]),
            "runner_up_new": pid(top_new[1][0]),
            "labour_breakeven": breakeven,
            "tpm_votes": t,
            "links": {"prelim_2026": {"url": RESULTS + "electionresults_2026_preliminary/",
                                      "xml": RESULTS + "electionresults_2026_preliminary/xml/e{0:02d}/e{0:02d}.xml".format(e)}},
        }
        # Candidate names of the winners (an independent has party None).
        entry["winner_new_candidate"] = next(c["candidate"] for c in cands if c["party"] == entry["winner_new"])
        entry["winner_prelim_candidate"] = next(c["candidate"] for c in cands if c["party"] == entry["winner_prelim"])
        electorates.append(entry)
        if w0 != w1:
            flips.append(entry["slug"])

    sensitivity = []
    for s in SHARES:
        won = Counter(winner_of(v) for v in by_share[s].values())
        fl = [gnames[e] for e in sorted(gnames) if winner_of(general[e]) != winner_of(by_share[s][e])]
        sensitivity.append({"share": s, "flips": fl, "labour": won[LABOUR], "national": won["National Party"]})

    maori_summary = [
        {"party": pid(party), "how": how, "votes": v}
        for (party, how), v in sorted(log.items(), key=lambda x: -x[1])]
    parties = {}
    for p in set(party_votes) | {party for rs in rows.values() for _, party, _ in rs}:
        if p != m.INDEPENDENT:
            parties[pid(p)] = pn.short_names.get(pid(p)) or unlisted[pid(p)]
    maori_total = sum(sum(t.values()) for _, _, t in places)
    national = {
        "parties": [{"id": i, "short": s} for i, s in sorted(parties.items(), key=lambda x: x[1])],
        "seats": {"counted": seats_c, "none": seats_n},
        "entitlement": {"counted": ent_c, "none": ent_n},
        "house": {"counted": house_c, "none": house_n},
        "party_vote_total": total_party,
        "tpm_party_share": party_votes[TPM] / total_party,
        "flips": flips,
        "maori_candidate_votes": maori_total,
        "moved": maori_summary,
        "sensitivity": sensitivity,
        "maori_electorates": [{"id": e, "name": n, "slug": slugify(n)} for e, n in sorted(maori_names.items())],
        "voting_places": len(places),
        "general_electorates": len(gnames),
        "sources": {
            "prelim_2026": {"label": "2026 preliminary count", "url": RESULTS + "electionresults_2026_preliminary/",
                            "xml": RESULTS + "electionresults_2026_preliminary/xml/election.xml"}},
    }
    os.makedirs(OUTDIR, exist_ok=True)
    for name, obj in [("national.json", national), ("electorates.json", electorates)]:
        path = os.path.join(OUTDIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        print("wrote {0} ({1:,} bytes)".format(path, os.path.getsize(path)))
    print("flips:", flips)
    print("sensitivity:", [(x["share"], len(x["flips"]), x["labour"], x["national"]) for x in sensitivity])
    print("houses:", house_c, house_n, "breakevens:",
          sorted((round(e["labour_breakeven"], 2), e["name"]) for e in electorates if e["labour_breakeven"] is not None)[-14:-4])


if __name__ == "__main__":
    main()
