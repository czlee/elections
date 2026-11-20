"""Downloads the per-voting-place results CSVs of an official count (2017, 2020
or 2023) from the Wayback Machine, and writes each electorate's party votes
split into ordinary, overseas and domestic special votes.

The XML feeds (download.py) don't label special votes for 2023: they're in
eNN.xml but not in any voting-place file. 2017's and 2020's XML has them as
voting places numbered 4xx, but which number holds which category varies
between electorates (NOTES.md). The CSVs label them in every year, as rows such as "Overseas
Special Votes Including Defence Force - Auckland Central", so they're used
for all three. The live site blocks them to scripts (NOTES.md), but the
Wayback Machine has every electorate's file for all three elections.

Categories, by the row label before " - <electorate>":
  overseas   "Overseas Special Votes Including Defence Force", and overseas
             party-only votes ("Overseas Votes Allowed for Party Only" in
             2020, "Overseas Special Votes for Party Only" in 2023; 2017 has
             no such row)
  domestic   "Special Votes BEFORE Polling Day", "Special Votes ON Polling
             Day" and "Votes Allowed for Party Only"
  ordinary   every other row: voting places, "Voting places where less than 6
             votes were taken", hospital teams, etc.

For each electorate and party, the three categories must add up to the CSV's
total row, and that must equal results/<year>/party_votes.csv
(download.py --election <year>), or the script stops with an error.

Raw CSVs (party and, for later use, candidate votes) are saved under
results/<year>/raw/csv/. The output is results/<year>/party_votes_by_category.csv,
with the official feed's party names.

--check-xml (2017 and 2020 only) also downloads each electorate's special-vote
voting-place files (vp_no 4xx) from the XML feed and reports any party whose
special votes there (all categories together) differ from the CSV's overseas
plus domestic votes. Warnings only. In 2020 the XML leaves out overseas
party-only votes in electorates that have no separate file for them (NOTES.md);
that difference is counted but not reported.
"""
import argparse
import csv
import io
import os
import re
import urllib.error
from collections import Counter, defaultdict

from download import ELECTIONS as FEEDS, fetch, write_csv
from parties import PartyNames
from scrape_wayback_prelim import fetch_capture, find_captures

ELECTIONS = ["2017", "2020", "2023"]
TYPES = ["party", "candidate"]
CSV_PATH = "electionresults_{0}/statistics/csv/"
CSV_PREFIX = "{0}-votes-by-voting-place-"

CATEGORIES = {
    "overseas special votes including defence force": "overseas",
    "overseas votes allowed for party only": "overseas",
    "overseas special votes for party only": "overseas",
    "special votes before polling day": "domestic",
    "special votes on polling day": "domestic",
    "votes allowed for party only": "domestic",
}
# A label matching this but not in CATEGORIES is an error, so that a special-vote
# row with an unexpected label can't be counted as ordinary. ("Special" alone
# would also catch voting places like "Wairau Valley Special School".)
SPECIAL_RE = re.compile(r"special votes|votes allowed", re.I)
NOT_PARTIES = {"Total Valid Party Votes", "Informal Party Votes"}
# Years whose XML feed has special-vote voting places, numbered 4xx (NOTES.md).
# Electorates have up to five; missing numbers are skipped.
XML_SPECIAL_YEARS = {"2017", "2020"}
XML_SPECIAL_VP_NOS = range(401, 410)


def parse_party_csv(text, elec_id):
    """Parses a party-votes-by-voting-place CSV. Returns (electorate name,
    {category: Counter({party: votes})}, Counter of the total row, Counter of
    the overseas party-only votes, which are also in "overseas")."""
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    match = re.fullmatch(r"(.*) (\d+)", rows[1][0].strip())
    if not match or match.group(2) != str(elec_id) or rows[1][1].strip() != "Party Vote Details":
        raise ValueError("electorate {0}: unexpected heading {1}".format(elec_id, rows[1]))
    name = match.group(1)
    parties = [p.strip() for p in rows[2][2:]]
    votes = {"ordinary": Counter(), "overseas": Counter(), "domestic": Counter()}
    overseas_party_only = Counter()
    for row in rows[3:]:
        label = row[1].strip() if len(row) > 1 else ""
        if label == name + " Total":
            total = Counter({p: int(v) for p, v in zip(parties, row[2:]) if p not in NOT_PARTIES})
            return name, votes, total, overseas_party_only
        if not label or not any(v.strip() for v in row[2:]):
            continue  # section heading, e.g. "Advance Voting Places"
        kind = label.split(" - ")[0].strip().lower()
        if kind in CATEGORIES:
            category = CATEGORIES[kind]
        elif SPECIAL_RE.search(label):
            raise ValueError("electorate {0}: unrecognised special-vote row {1!r}".format(elec_id, label))
        else:
            category = "ordinary"
        for party, value in zip(parties, row[2:]):
            if party not in NOT_PARTIES and value.strip():
                votes[category][party] += int(value)
                if category == "overseas" and "party only" in kind:
                    overseas_party_only[party] += int(value)
    raise ValueError("electorate {0}: no {1!r} row".format(elec_id, name + " Total"))


def read_official(year):
    """Reads results/<year>/party_votes.csv as {elec_id: Counter({party: votes})}."""
    official = defaultdict(Counter)
    with open(os.path.join("results", year, "party_votes.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            official[int(row["elec_id"])][row["party"]] += int(row["votes"])
    return official


def download(year, kind, rawdir, force=False):
    """Downloads every electorate's CSV of one kind. Returns {elec_id: filename}."""
    prefix = CSV_PREFIX.format(kind)
    captures = find_captures(CSV_PATH.format(year), prefix, ".csv")
    print("{0} {1}: found captures for {2} electorates".format(year, kind, len(captures)))
    files = {}
    for e_no, (timestamp, original) in sorted(captures.items(), key=lambda c: int(c[0])):
        filename = os.path.join(rawdir, "{0}{1}.csv".format(prefix, e_no))
        fetch_capture(timestamp, original, filename, force)
        files[int(e_no)] = filename
    return files


def check_xml(year, by_elec):
    """Compares by_elec ({elec_id: {category: Counter({party: votes})}}, with
    the overseas party-only votes also as "overseas party-only") with the XML
    feed's special-vote voting places. Prints any unexplained differences."""
    base, rawdir = FEEDS[year], os.path.join("results", year, "raw")
    parties = {p.get("p_no"): p.findtext("short_name") for p in fetch(base, "parties.xml", rawdir)}
    problems, missing_party_only = 0, Counter()
    for elec_id, categories in sorted(by_elec.items()):
        xml = Counter()
        for vp_no in XML_SPECIAL_VP_NOS:
            path = "e{0:02d}/votingplaces/{0:02d}-{0:02d}{1:03d}.xml".format(elec_id, vp_no)
            try:
                root = fetch(base, path, rawdir)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue
                raise
            for party in root.find("partyvotes"):
                xml[parties[party.get("p_no")]] += int(party.findtext("votes"))
        csv_specials = categories["overseas"] + categories["domestic"]
        if +xml != +csv_specials and +(xml + categories["overseas party-only"]) == +csv_specials:
            missing_party_only[elec_id] = sum(categories["overseas party-only"].values())
        elif +xml != +csv_specials:
            print("  {0} electorate {1}: XML special votes {2:,}, CSV {3:,}".format(
                year, elec_id, sum(xml.values()), sum(csv_specials.values())))
            problems += 1
    print("{0}: XML check, {1} problem(s) in {2} electorates".format(year, problems, len(by_elec)))
    if missing_party_only:
        print("  (XML leaves out the overseas party-only votes in {0} electorates, {1} votes in all)".format(
            len(missing_party_only), sum(missing_party_only.values())))


def main(year, types, force=False, xml=False):
    rawdir = os.path.join("results", year, "raw", "csv")
    files = {kind: download(year, kind, rawdir, force) for kind in types}
    if "party" not in files:
        return

    official = read_official(year)
    names = PartyNames()
    if set(files["party"]) != set(official):
        raise ValueError("{0}: electorates {1} are in only one of the CSVs and party_votes.csv".format(
            year, sorted(set(files["party"]) ^ set(official))))

    rows, national, by_elec = [], defaultdict(Counter), {}
    for elec_id in sorted(official):
        with open(files["party"][elec_id], encoding="utf-8") as f:
            name, votes, total, overseas_party_only = parse_party_csv(f.read(), elec_id)
        # Resolve the CSV's names to the official feed's through party_ids, as
        # the CSVs use some different names (e.g. "Leighton Baker Party").
        official_names = {names.party_id(year, p): p for p in official[elec_id]}
        to_official = {p: official_names[names.party_id(year, p)] for p in total}
        summed = Counter()
        for category in votes:
            summed.update(votes[category])
        for party in total:
            if summed[party] != total[party]:
                raise ValueError("{0} {1} {2}: categories sum to {3}, total row says {4}".format(
                    year, name, party, summed[party], total[party]))
        total_official = Counter({to_official[p]: v for p, v in total.items()})
        if +total_official != +official[elec_id]:
            raise ValueError("{0} {1}: CSV totals don't match party_votes.csv: {2}".format(
                year, name, {p: (total_official[p], official[elec_id][p])
                             for p in set(total_official) | set(official[elec_id])
                             if total_official[p] != official[elec_id][p]}))
        by_elec[elec_id] = {c: Counter() for c in votes}
        by_elec[elec_id]["overseas party-only"] = Counter({to_official[p]: v for p, v in overseas_party_only.items()})
        for category, counts in votes.items():
            for party, value in counts.items():
                rows.append([elec_id, name, to_official[party], category, value])
                national[category][to_official[party]] += value
                by_elec[elec_id][category][to_official[party]] += value

    write_csv(os.path.join("results", year, "party_votes_by_category.csv"),
              ["elec_id", "elec_name", "party", "category", "votes"], rows)
    print("{0}: ordinary {1:,}, overseas {2:,}, domestic {3:,}".format(
        year, *(sum(national[c].values()) for c in ["ordinary", "overseas", "domestic"])))
    if xml and year in XML_SPECIAL_YEARS:
        check_xml(year, by_elec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-e", "--election", choices=ELECTIONS, action="append",
                        help="election to download (repeatable; default: all)")
    parser.add_argument("--types", default=",".join(TYPES),
                        help="comma-separated kinds of CSV to download (default: %(default)s)")
    parser.add_argument("-f", "--force", action="store_true", help="re-download files that already exist")
    parser.add_argument("--check-xml", action="store_true",
                        help="also compare 2017's and 2020's special votes with the XML feed (slow)")
    args = parser.parse_args()
    types = args.types.split(",")
    if not set(types) <= set(TYPES):
        parser.error("--types must be from " + ",".join(TYPES))
    for year in args.election or ELECTIONS:
        main(year, types, args.force, args.check_xml)
