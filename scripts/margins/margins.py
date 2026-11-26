"""Two things from an election's results, for a quick write-up when the final
count comes out:

  1. For each party, how many party votes it would take to gain or lose a seat.
  2. The electorates with the closest margins.

Input is data/elections/<election>/ from download.py (party_votes.csv and
candidate_votes.csv), e.g. `margins.py 2026-prelim`. Output goes to
results/margins/<election>/: index.html (self-contained), margins.json (all of it,
for a site, with the whole House in each scenario), parties.csv and
electorates.csv, and a summary is printed.

Method for (1). Seats come from seats.py: Sainte-Laguë among qualifying
parties, with the electorates a party has won kept whatever its share (see
that file). We then change ONE party's party vote, holding every other party's
votes and all electorate results fixed, and find (by search, on the real
allocation, so the 5% threshold and overhang are handled) the smallest change
at which that party's seat count changes:

  - "to gain": the fewest extra party votes at which the party certainly has
    one more seat. (Exactly one vote fewer is either no change or a tie for
    the last seat, which the Act settles by lot.) The extra votes also count
    in the total used for the 5% threshold, so they can push another party
    under the line.
  - "to lose": likewise, the fewest party votes removed at which the party
    certainly has one fewer seat.
  - "None" means no number of votes does it: a party with no entitlement
    (e.g. one that qualifies only through an electorate, on a tiny party vote)
    has no seat to lose. Overhang doesn't cause it: the entitlement still
    changes, and the number is starred.

"Seats" here means a party's Sainte-Laguë entitlement, ignoring overhang: the
seats it would have from the party vote alone. A party that wins more
electorates than that is in overhang, but a gain or loss in its entitlement
still matters, since it changes how big the overhang is (and so the House) and
which other parties' seats move. For each change we also report which other
parties' entitlements change at that point. Electorates don't move: a party
vote can't change them.
The main tables list only parties that qualify for seats. A party with no
electorate that is within --near points of the 5% threshold (either side)
gets a separate section instead: the votes it would take to reach the
threshold (or drop below it), and every party's entitlement change when it
does. There's no such section when no party is that close.
"""
import argparse
import csv
import datetime
import html
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import seats
from parties import PartyNames

SEARCH_LIMIT = 10  # give up looking for a gain beyond this many times the total vote


def read_csv(election, name):
    with open(os.path.join("data", "elections", election, name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def party_totals(rows):
    totals = Counter()
    for row in rows:
        totals[row["party"]] += int(row["votes"])
    return dict(totals)


def electorate_results(rows):
    """Returns {elec_id: {"name", "candidates": [(votes, candidate, party)] sorted highest first}}."""
    result = {}
    for row in rows:
        e = result.setdefault(row["elec_id"], {"name": row["elec_name"], "candidates": []})
        e["candidates"].append((int(row["votes"]), row["candidate"], row["party"]))
    for e in result.values():
        e["candidates"].sort(reverse=True)
    return result


def count_electorates(results, votes):
    """Returns ({party: electorates won}, electorates won by someone else, e.g. an independent or a
    party with no list). Skips an electorate with no votes at all (2023's Port Waikato, whose
    election was postponed) and raises on a tie for first."""
    won, other = Counter(), 0
    for e_id, e in results.items():
        top = e["candidates"]
        if top[0][0] == 0:
            continue
        if len(top) > 1 and top[0][0] == top[1][0]:
            raise ValueError("{0}: tie for first".format(e["name"]))
        party = top[0][2]
        if party in votes:
            won[party] += 1
        else:
            other += 1
    return dict(won), other


def allocation(votes, electorates, other):
    """Returns ({party: (fewest, most) Sainte-Laguë seats it could be entitled to}, whether there's a
    tie). The two differ only when a tie for the last seat is to be decided by lot."""
    qualified, to_allocate, quotients = seats._quotients(votes, electorates, other, seats.TOTAL_SEATS,
                                                         seats.THRESHOLD)
    boundary = quotients[to_allocate - 1][0]
    tie = len(quotients) > to_allocate and quotients[to_allocate][0] == boundary
    # Without a tie, the seats go to exactly the quotients >= boundary. In a tie, the quotients equal
    # to the boundary are in doubt: "fewest" counts none of them, "most" counts all of them.
    fewest, most = Counter(), Counter()
    for q, p, _ in quotients:
        if q > boundary or (q == boundary and not tie):
            fewest[p] += 1
        if q >= boundary:
            most[p] += 1
    result = {}
    for p in set(votes) | set(electorates):
        result[p] = (fewest.get(p, 0), most.get(p, 0))
    return result, tie


def with_votes(votes, party, delta):
    changed = dict(votes)
    changed[party] = changed[party] + delta
    return changed


def search(predicate, limit):
    """Smallest k in [1, limit] with predicate(k) true (it must be monotone), or None."""
    if not predicate(limit):
        return None
    lo, hi = 0, limit  # predicate(lo) false, predicate(hi) true
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if predicate(mid):
            hi = mid
        else:
            lo = mid
    return hi


def party_margins(votes, electorates, other):
    """Returns the list of dicts described in the module docstring, one per party in `votes`."""
    base, tie = allocation(votes, electorates, other)
    if tie:
        raise seats.TieError("tied for the last seat as the results stand")
    base_seats = {p: s[0] for p, s in base.items()}
    qualified = seats._quotients(votes, electorates, other, seats.TOTAL_SEATS, seats.THRESHOLD)[0]
    total = sum(votes.values())
    rows = []
    for party in sorted(votes, key=lambda p: -votes[p]):
        row = {"party": party, "votes": votes[party], "share": votes[party] / total,
               "electorates": electorates.get(party, 0), "seats": base_seats[party], "qualified": party in qualified}
        row["overhang"] = max(0, row["electorates"] - row["seats"])
        # The quotient for a party's nth seat is votes / (2n - 1); its entitlement is the number of its
        # quotients in the top 120 (less other electorates). Parties that don't qualify have none.
        n = row["seats"]
        row["last_divisor"], row["last_quotient"] = (2 * n - 1, votes[party] / (2 * n - 1)) if n else (None, None)
        row["next_divisor"] = 2 * n + 1 if party in qualified else None
        row["next_quotient"] = votes[party] / row["next_divisor"] if party in qualified else None

        def seats_with(delta):
            return allocation(with_votes(votes, party, delta), electorates, other)[0]

        def change(q, after):
            """(q, entitlement change, True if q's seats don't change: it's won at least as many electorates
            as its entitlement before and after, so only its overhang changes)."""
            before, now, won = base_seats.get(q, 0), after[q][0], electorates.get(q, 0)
            return q, now - before, max(before, won) == max(now, won)

        def effects(delta):
            """Other parties' entitlement changes with `delta` extra votes for the party: [(party, change,
            whether it only changes the party's overhang)], and the same for the party itself."""
            after = seats_with(delta)
            return [change(q, after) for q in after if q != party and after[q][0] != base_seats.get(q, 0)], \
                change(party, after)[2], {q: after[q][0] for q in after}

        row["gain"] = search(lambda k: seats_with(k)[party][0] > base_seats[party], total * SEARCH_LIMIT)
        row["gain_effects"], row["gain_overhang"], row["gain_after"] = \
            effects(row["gain"]) if row["gain"] else ([], False, None)

        row["lose"] = search(lambda k: seats_with(-k)[party][1] < base_seats[party], votes[party])
        row["lose_effects"], row["lose_overhang"], row["lose_after"] = \
            effects(-row["lose"]) if row["lose"] else ([], False, None)

        # A party with no electorate depends on the threshold: how far from it, and what crossing it does.
        row["threshold"] = None
        if not row["electorates"]:
            def qualifies(delta):
                return party in seats._quotients(with_votes(votes, party, delta), electorates, other,
                                                 seats.TOTAL_SEATS, seats.THRESHOLD)[0]

            if row["qualified"]:
                k, delta, direction = search(lambda k: not qualifies(-k), votes[party]), None, "drop below"
                delta = -k if k else None
            else:
                k, direction = search(lambda k: qualifies(k), total * SEARCH_LIMIT), "reach"
                delta = k
            if k:
                after = seats_with(delta)
                changes = [change(q, after) for q in after if after[q][0] != base_seats.get(q, 0)]
                changes.sort(key=lambda c: c[0] != party)  # the party itself first
                row["threshold"] = {"direction": direction, "votes": k, "changes": changes,
                                    "after": {q: after[q][0] for q in after}}
        rows.append(row)
    return rows


def electorate_margins(results):
    rows = []
    for e_id, e in results.items():
        top = e["candidates"]
        if top[0][0] == 0:
            continue
        valid = sum(c[0] for c in top)
        (v1, n1, p1), (v2, n2, p2) = top[0], top[1]
        rows.append({"id": int(e_id), "electorate": e["name"], "winner": n1, "winner_party": p1, "winner_votes": v1,
                     "runner_up": n2, "runner_up_party": p2, "runner_up_votes": v2,
                     "margin": v1 - v2, "margin_pct": 100 * (v1 - v2) / valid})
    rows.sort(key=lambda r: r["margin"])
    return rows


def display_name(names, election, party):
    year = election[:4]
    party_id = names.ids.get((year, party))
    return names.short_names.get(party_id, party.strip()) if party_id else party.strip()


def tidy_candidate(name):
    """'SURNAME, Given' -> 'Given Surname'."""
    if "," in name:
        surname, given = [s.strip() for s in name.split(",", 1)]
        return "{0} {1}".format(given, surname.title())
    return name


# --- Output ---

CSS = """body{font:15px/1.4 system-ui,sans-serif;max-width:60em;margin:1em auto;padding:0 1em;color:#222}
table{border-collapse:collapse;width:100%;margin:.5em 0 1.5em}th,td{padding:.25em .6em;border-bottom:1px solid #ddd;
text-align:left}th{border-bottom:2px solid #888}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.note{color:#555;font-size:.9em}.none{color:#999}"""


def relevant(row):
    """Whether a party gets a line in the main tables: those that qualify for seats (the CSV has all)."""
    return row["qualified"]


def near_threshold(row, near):
    """Whether a party with no electorate is within `near` (a share, e.g. 0.02) of the 5% threshold."""
    return row["threshold"] is not None and abs(row["share"] - seats.THRESHOLD) <= near


def describe(label, changes):
    """E.g. "Labour −1, ACT +1*" (* means it only changes that party's overhang)."""
    return ", ".join("{0} {1:+d}{2}".format(label(p), d, "*" if overhang else "").replace("-", "−")
                     for p, d, overhang in changes)


def quotient_cells(quotient, divisor):
    if quotient is None:
        return "<td class='n none'>–<td class='n none'>–"
    return "<td class=n>{0}<td class=n>{1}".format(fmt(round(quotient)), divisor)


def fmt(n):
    return "{0:,}".format(n)


def write_html(filename, title, updated, party_rows, elec_rows, label, shown, ladder, to_allocate, near):
    def votes_cell(n, overhang=False):
        return '<td class="n none">–</td>' if n is None else '<td class="n">{0}{1}</td>'.format(
            fmt(n), "*" if overhang else "")

    def who(changes):
        return describe(label, changes)

    out = ["<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>",
           "<title>{0}</title><style>{1}</style>".format(html.escape(title), CSS),
           "<h1>{0}</h1>".format(html.escape(title)),
           "<p class=note>From the Electoral Commission's results as of {0}.</p>".format(html.escape(updated)),
           "<h2>Party vote: votes to gain or lose a seat</h2>",
           "<p class=note>Extra (or fewer) party votes for that party alone, everyone else unchanged, at which "
           "its seat count changes. – means it can't (a party with no seat can't lose one).</p>",
           "<table><tr><th>Party<th class=n>Party votes<th class=n>%<th class=n>Entitlement"
           "<th class=n>Votes to gain<th>Gain from<th class=n>Votes to lose<th>Lose from</tr>"]
    for r in party_rows:
        if not relevant(r):
            continue
        out.append("<tr><td>{0}<td class=n>{1}<td class=n>{2:.2f}<td class=n>{3}".format(
            html.escape(label(r["party"])), fmt(r["votes"]), 100 * r["share"], r["seats"]) +
            votes_cell(r["gain"], r["gain_overhang"]) + "<td>{0}".format(html.escape(who(r["gain_effects"]))) +
            votes_cell(r["lose"], r["lose_overhang"]) + "<td>{0}</tr>".format(html.escape(who(r["lose_effects"]))))
    out.append("</table>")
    out.append("<p class=note>* Only changes the overhang: the party has won at least as many electorates as its "
               "entitlement before and after, so its seats don't change.</p>")
    close = [r for r in party_rows if near_threshold(r, near)]
    if close:  # most elections have no such party, so there's no section then
        out.append("<h2>Near the 5% threshold</h2>")
        out.append("<p class=note>Parties with no electorate seat, within {0:g} percentage points of the "
                   "threshold: the party votes they'd need to gain or lose to qualify (or stop qualifying), and "
                   "the change in everyone's entitlement when they do.</p>".format(100 * near))
        out.append("<table><tr><th>Party<th class=n>Party votes<th class=n>%<th>Needs to<th class=n>Votes"
                   "<th>Seat changes</tr>")
        for r in close:
            t = r["threshold"]
            out.append("<tr><td>{0}<td class=n>{1}<td class=n>{2:.2f}<td>{3} 5%<td class=n>{4}<td>{5}</tr>".format(
                html.escape(label(r["party"])), fmt(r["votes"]), 100 * r["share"], t["direction"], fmt(t["votes"]),
                html.escape(who(t["changes"]))))
        out.append("</table>")
    out.append("<h2>Sainte-Laguë quotients</h2>")
    out.append("<p class=note>A party's nth seat has quotient votes ÷ (2n − 1). The {0} highest quotients get the "
               "Sainte-Laguë seats (120, less electorates won by independents or parties without a list). "
               "Each party's last seat in and first seat out are below; compare them with the last quotient "
               "in (no. {0}) and the first out (no. {1}) in the ranking.</p>".format(to_allocate, to_allocate + 1))
    out.append("<table><tr><th>Party<th class=n>Party votes<th class=n>Seats<th class=n>Last in<th class=n>÷"
               "<th class=n>Next out<th class=n>÷</tr>")
    for r in party_rows:
        if not relevant(r):
            continue
        out.append("<tr><td>{0}<td class=n>{1}<td class=n>{2}".format(html.escape(label(r["party"])), fmt(r["votes"]),
                                                                       r["seats"]) +
                   quotient_cells(r["last_quotient"], r["last_divisor"]) +
                   quotient_cells(r["next_quotient"], r["next_divisor"]) + "</tr>")
    out.append("</table>")
    out.append("<table><tr><th class=n>Rank<th>Party<th class=n>Its seat<th class=n>Quotient</tr>")
    for r in ladder:
        style = " style='border-bottom:2px solid #222'" if r["rank"] == to_allocate else ""
        out.append("<tr{4}{5}><td class=n>{0}<td>{1}<td class=n>{2}<td class=n>{3}</tr>".format(
            r["rank"], html.escape(label(r["party"])), r["seat"], fmt(round(r["quotient"])), style,
            "" if r["allocated"] else " class=none"))
    out.append("</table>")
    out.append("<h2>Closest electorates</h2><table><tr><th class=n>Margin<th class=n>%<th>Electorate<th>Winner"
               "<th>Runner-up</tr>")
    for r in elec_rows[:shown]:
        out.append("<tr><td class=n>{0}<td class=n>{1:.2f}<td>{2}<td>{3} ({4}, {5})<td>{6} ({7}, {8})</tr>".format(
            fmt(r["margin"]), r["margin_pct"], html.escape(r["electorate"]),
            html.escape(tidy_candidate(r["winner"])), html.escape(label(r["winner_party"])), fmt(r["winner_votes"]),
            html.escape(tidy_candidate(r["runner_up"])), html.escape(label(r["runner_up_party"])),
            fmt(r["runner_up_votes"])))
    out.append("</table>")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def composition(entitlements, electorates, other, label, pid):
    """The House if parties had these Sainte-Laguë entitlements (and the same electorates): a list of
    {"party", "id", "name", "entitlement", "electorates", "seats", "list"} for each party with a seat, and the
    House size."""
    parties = []
    for p in set(entitlements) | set(electorates):
        e, won = entitlements.get(p, 0), electorates.get(p, 0)
        if e or won:
            parties.append({"party": p, "id": pid(p), "name": label(p), "entitlement": e, "electorates": won,
                            "seats": max(e, won), "list": max(e, won) - won})
    parties.sort(key=lambda r: (-r["seats"], r["party"]))
    return {"parties": parties, "other_electorates": other, "house": sum(r["seats"] for r in parties) + other}


def build_json(election, updated, party_rows, elec_rows, label, pid, ladder, to_allocate, electorates, other, near):
    """Everything the page shows, for a site to present. Each scenario (the party gaining or losing a seat
    on the party vote, or crossing the 5% threshold) has the votes it takes and the whole resulting House,
    so a site can show it without knowing the electoral rules. Parties have an "id" (the stable party_id from
    party_names.toml, null if it has none) so a site can colour them."""
    def scenario(row, direction, votes, after, extra=None):
        result = {"direction": direction, "votes": votes, "house": composition(after, electorates, other, label, pid)}
        result.update(extra or {})
        return result

    parties = []
    for r in party_rows:
        entry = {"party": r["party"], "id": pid(r["party"]), "name": label(r["party"]), "votes": r["votes"], "share": r["share"],
                 "qualified": r["qualified"], "entitlement": r["seats"], "electorates": r["electorates"],
                 "overhang": r["overhang"],
                 "last": None if r["last_divisor"] is None else
                 {"quotient": r["last_quotient"], "divisor": r["last_divisor"]},
                 "next": None if r["next_divisor"] is None else
                 {"quotient": r["next_quotient"], "divisor": r["next_divisor"]},
                 "gain": None, "lose": None, "threshold": None}
        if r["gain"]:
            entry["gain"] = scenario(r, "gain", r["gain"], r["gain_after"], {"overhang_only": r["gain_overhang"]})
        if r["lose"]:
            entry["lose"] = scenario(r, "lose", r["lose"], r["lose_after"], {"overhang_only": r["lose_overhang"]})
        if r["threshold"]:
            t = r["threshold"]
            entry["threshold"] = scenario(r, t["direction"], t["votes"], t["after"],
                                          {"near": near_threshold(r, near)})
        parties.append(entry)
    base = {r["party"]: r["seats"] for r in party_rows}
    return {"election": election, "updated": updated, "generated": datetime.date.today().isoformat(),
            "total_seats": seats.TOTAL_SEATS, "threshold": seats.THRESHOLD, "near": near,
            "to_allocate": to_allocate, "house": composition(base, electorates, other, label, pid),
            "parties": parties,
            "ladder": [dict(r, id=pid(r["party"]), name=label(r["party"])) for r in ladder],
            "electorates": [dict(r, winner_party_id=pid(r["winner_party"]), winner_party_name=label(r["winner_party"]),
                                 runner_up_party_id=pid(r["runner_up_party"]),
                                 runner_up_party_name=label(r["runner_up_party"])) for r in elec_rows]}


def write_csv(filename, rows, columns):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for r in rows:
            writer.writerow(["; ".join("{0} {1:+d}{2}".format(change[0], change[1], "*" if change[2] else "") for change in r[c]) if isinstance(r.get(c), list)
                             else r.get(c, "") for c in columns])


def main(election, shown, outdir, near):
    for name in ["party_votes.csv", "candidate_votes.csv"]:
        if not os.path.exists(os.path.join("data", "elections", election, name)):
            sys.exit("no data/elections/{0}/{1}: run `python3 scripts/download.py --election {0}` first "
                     "(or with --base <URL>, see README.md)".format(election, name))
    names = PartyNames()
    votes = party_totals(read_csv(election, "party_votes.csv"))
    results = electorate_results(read_csv(election, "candidate_votes.csv"))
    electorates, other = count_electorates(results, votes)

    def label(party):
        return display_name(names, election, party)

    def pid(party):
        return names.ids.get((election[:4], party))

    party_rows = party_margins(votes, electorates, other)
    ladder, to_allocate = seats.quotient_ladder(votes, electorates, other, before=8, after=8)
    elec_rows = electorate_margins(results)

    national = {r["statistic"]: r["value"] for r in read_csv(election, "national_stats.csv")} \
        if os.path.exists(os.path.join("data", "elections", election, "national_stats.csv")) else {}
    updated = national.get("updated") or "(unknown)"
    os.makedirs(outdir, exist_ok=True)
    write_html(os.path.join(outdir, "index.html"), "Election {0}: margins".format(election), updated, party_rows,
               elec_rows, label, shown, ladder, to_allocate, near)
    with open(os.path.join(outdir, "margins.json"), "w", encoding="utf-8") as f:
        json.dump(build_json(election, updated, party_rows, elec_rows, label, pid, ladder, to_allocate,
                             electorates, other, near), f, ensure_ascii=False, indent=1)
    write_csv(os.path.join(outdir, "parties.csv"), party_rows,
              ["party", "votes", "share", "seats", "electorates", "overhang", "last_quotient", "last_divisor",
               "next_quotient", "next_divisor", "gain", "gain_effects", "lose",
               "lose_effects"])
    write_csv(os.path.join(outdir, "electorates.csv"), elec_rows,
              ["id", "electorate", "winner", "winner_party", "winner_votes", "runner_up", "runner_up_party",
               "runner_up_votes", "margin", "margin_pct"])

    print("{0}  (updated {1}); House of {2}".format(
        election, updated, sum(max(r["seats"], r["electorates"]) for r in party_rows) + other))
    print("{0:<24}{1:>10}{2:>6}{3:>9}  {4:<46}{5:>8}  {6}".format(
        "party", "votes", "seats", "to gain", "gain from", "to lose", "lose from"))
    for r in party_rows:
        if not relevant(r):
            continue
        print("{0:<24}{1:>10}{2:>6}{3:>9}  {4:<46}{5:>8}  {6}".format(
            label(r["party"])[:23], fmt(r["votes"]), r["seats"],
            "-" if r["gain"] is None else fmt(r["gain"]) + ("*" if r["gain_overhang"] else ""),
            describe(label, r["gain_effects"]),
            "-" if r["lose"] is None else fmt(r["lose"]) + ("*" if r["lose_overhang"] else ""),
            describe(label, r["lose_effects"])))
    print("* only changes the overhang (the party has won at least as many electorates as its entitlement)")
    close = [r for r in party_rows if near_threshold(r, near)]
    if close:
        print("\nnear the 5% threshold (no electorate, within {0:g} points):".format(100 * near))
    for r in close:
        t = r["threshold"]
        print("  {0:<22}{1:>10} ({2:.2f}%): {3} 5% with {4} votes: {5}".format(
            label(r["party"])[:21], fmt(r["votes"]), 100 * r["share"], t["direction"], fmt(t["votes"]),
            describe(label, t["changes"])))
    print("\nSainte-Laguë quotients (votes / divisor); the last seat is no. {0}:".format(to_allocate))
    print("{0:<24}{1:>6}{2:>12}{3:>6}{4:>12}{5:>6}".format("party", "seats", "last in", "÷", "next out", "÷"))
    for r in party_rows:
        if relevant(r):
            cells = ["-" if r[k] is None else fmt(round(r[k])) if "quotient" in k else str(r[k])
                     for k in ("last_quotient", "last_divisor", "next_quotient", "next_divisor")]
            print("{0:<24}{1:>6}{2:>12}{3:>6}{4:>12}{5:>6}".format(label(r["party"])[:23], r["seats"], *cells))
    for r in ladder:
        if r["rank"] in (to_allocate, to_allocate + 1):
            print("  no. {0}: {1} seat {2}, quotient {3}".format(r["rank"], label(r["party"]), r["seat"],
                                                                 fmt(round(r["quotient"]))))
    print("\nclosest electorates:")
    for r in elec_rows[:shown]:
        print("  {0:>6}  {1:<24} {2} ({3}) over {4} ({5})".format(
            fmt(r["margin"]), r["electorate"], tidy_candidate(r["winner"]), label(r["winner_party"]),
            tidy_candidate(r["runner_up"]), label(r["runner_up_party"])))
    print("\nwrote {0}/".format(outdir))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("election", help="a directory name in data/elections/, e.g. 2026-prelim or 2023")
    parser.add_argument("-n", "--shown", type=int, default=15, help="how many electorates to show (default: 15)")
    parser.add_argument("--near", type=float, default=1.0,
                        help="how many percentage points from the 5%% threshold counts as near (default: 1)")
    parser.add_argument("-o", "--outdir", help="output directory (default: results/margins/<election>)")
    args = parser.parse_args()
    main(args.election, args.shown, args.outdir or os.path.join("results", "margins", args.election),
         args.near / 100)
