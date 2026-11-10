"""Allocates seats in the New Zealand House of Representatives under MMP, as in
section 191 of the Electoral Act 1993:

  - A party qualifies if it got at least 5% of all valid party votes or won at
    least one electorate.
  - The 120 seats, less the electorates won by candidates who aren't from a
    qualifying party (e.g. independents), are shared among qualifying parties
    by Sainte-Laguë: each seat goes to the highest remaining quotient
    votes / (2s + 1), where s is the seats the party has so far.
  - A party keeps all the electorates it wins. If that's more than its share
    (overhang), it keeps the extra seats and the House gets bigger; other
    parties' shares aren't reduced.

A tie for the last seat is decided by lot under the Act; allocate() raises an
error instead. Doesn't handle a party list running out of candidates.

Run `python3 seats.py` to check the allocation against the Electoral
Commission's in results/*/raw/election.xml.
"""
import os
import xml.etree.ElementTree as ET

TOTAL_SEATS = 120
THRESHOLD = 0.05


class TieError(Exception):
    pass


def allocate(votes, electorates, other_electorates=0, total_seats=TOTAL_SEATS, threshold=THRESHOLD):
    """Allocates seats.

    votes: {party: valid party votes}, for every party (used for the threshold).
    electorates: {party: electorates won}, for parties eligible for list seats.
    other_electorates: electorates won by candidates not from those parties
        (independents, unregistered parties).

    Returns {party: (electorate_seats, list_seats, total_seats)} for every
    party in `votes` or `electorates`.
    """
    total_votes = sum(votes.values())
    qualified = [p for p in votes if votes[p] >= threshold * total_votes or electorates.get(p, 0) > 0]
    to_allocate = total_seats - other_electorates

    # Sainte-Laguë: the to_allocate highest quotients among qualified parties.
    quotients = sorted(((votes[p] / (2 * s + 1), p) for p in qualified for s in range(to_allocate)),
                       reverse=True)
    if len(quotients) > to_allocate and quotients[to_allocate - 1][0] == quotients[to_allocate][0]:
        tied = sorted(p for q, p in quotients if q == quotients[to_allocate][0])
        raise TieError("tie for the last seat between {0}".format(", ".join(map(str, tied))))
    entitlement = {p: 0 for p in qualified}
    for q, p in quotients[:to_allocate]:
        entitlement[p] += 1

    result = {}
    for p in set(votes) | set(electorates):
        won = electorates.get(p, 0)
        seats = max(entitlement.get(p, 0), won)
        result[p] = (won, seats - won, seats)
    return result


def check_feed(filename):
    """Allocates seats from an election.xml and compares with the seats it
    reports. Returns a list of mismatch descriptions (empty if it matches)."""
    root = ET.parse(filename).getroot()
    votes, electorates, expected = {}, {}, {}
    for party in root.find("partystatus"):
        p = party.get("p_no")
        votes[p] = int(party.findtext("votes"))
        electorates[p] = int(party.findtext("candidate_seats"))
        expected[p] = (electorates[p], int(party.findtext("party_seats")), int(party.findtext("total_seats")))
    # No independents won electorates in the feeds we have. (Don't infer them
    # from total_electorates_final: 2023's 72 includes Port Waikato, which was
    # decided in a by-election after the seats were allocated.)
    other = 0
    result = allocate(votes, electorates, other)
    mismatches = ["p_no {0}: got {1}, expected {2}".format(p, result[p], expected[p])
                  for p in sorted(expected, key=int) if result[p] != expected[p]]
    return mismatches, sum(r[2] for r in result.values()), other


def main():
    for election in ["2017", "2020", "2023", "2026-prelim"]:
        filename = os.path.join("results", election, "raw", "election.xml")
        if not os.path.exists(filename):
            print("{0}: no {1}, skipped".format(election, filename))
            continue
        mismatches, house, other = check_feed(filename)
        print("{0}: {1} seats ({2} other electorates): {3}".format(
            election, house, other, "matches" if not mismatches else "MISMATCH"))
        for m in mismatches:
            print("    " + m)


if __name__ == "__main__":
    main()
