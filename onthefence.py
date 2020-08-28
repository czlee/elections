"""Web scraper for On the Fence results page.

Subject to break if On the Fence changes its web page layout.

Chuan-Zheng Lee <czlee@stanford.edu>
August 2020
"""

from bs4 import BeautifulSoup
import argparse
import csv
import json
import re
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("file", type=argparse.FileType("r"))
parser.add_argument("-j", "--json", metavar="FILE", type=argparse.FileType("w"),
    help="Write JSON to this output file")
parser.add_argument("-c", "--csv", metavar="FILE", type=argparse.FileType("w"),
    help="Write CSV to this output file")
parser.add_argument("-q", "-quiet", action="store_false", dest="print",
    help="Don't print summary output")
parser.add_argument("-x", "--no-your-response", action="store_false", dest="include_your_response",
    help="Exclude the 'Your Response' column")
args = parser.parse_args()

soup = BeautifulSoup(args.file.read(), "html.parser")
grid = soup.find_all("section")[5].div.find("div", "grid")
items = grid.find_all("div", "grid-item")

scraped = []

# Percentage scale questions

for item in items[:12]:
    question = {}

    results = item.find("div", "result-stats-wrapper")
    parties = results.find_all("p")
    parties = [p for p in parties if "no-response" not in p.get("class", [])]
    positions = results.find_all("div", "result-chart")
    assert(len(parties) == len(positions))

    question["parties"] = []
    for party, position in zip(parties, positions):
        data = {}
        data["party"] = party.text

        if position.div:
            match = re.match(r"left: (\d+)%;", position.div.div["style"])
            left = match.group(1)
            data["position"] = int(left) / 50
        elif position.p and "no-response" in position.p.get("class", []):
            data["position"] = None
        else:
            raise AssertionError

        if data["party"] != "Your Response" or args.include_your_response:
            question["parties"].append(data)

    back = item.find("div", "back")
    question["title"] = back.div.h2.text
    question["text"] = back.div.div.p.text
    issue_options = back.find("div", "issue-options")
    question["left-option"] =  issue_options.find("span", "text-left").text
    question["right-option"] =  issue_options.find("span", "text-right").text
    question["type"] = "scale"

    scraped.append(question)

# Likert questions

for item in items[12:]:
    question = {}

    results = item.find("div", "result-stats-wrapper")
    parties = results.find_all("p")
    positions = results.find_all("div", "result-lines")
    assert(len(parties) == len(positions))
    question["parties"] = []
    for party, position in zip(parties, positions):
        data = {}
        data["party"] = party.text
        selected = ["selected" in x["class"] for x in position.find_all("div", "full-width")]
        data["position"] = selected.index(True) + 1

        if data["party"] != "Your Response" or args.include_your_response:
            question["parties"].append(data)

    back = item.find("div", "back")
    question["title"] = back.div.h2.text
    question["text"] = back.div.div.text
    question["type"] = "likert"

    scraped.append(question)


scraped.sort(key=lambda q: (q["type"] == "likert", q["title"]))


if args.json:
    json.dump(scraped, args.json, indent=4)


if args.csv or args.print:

    parties = set(data["party"] for question in scraped for data in question["parties"])
    parties = sorted(parties)

    position_columns = []
    for question in scraped:
        positions_by_party = {data["party"]: data["position"] for data in question["parties"]}
        positions = [positions_by_party.get(party) for party in parties]
        position_columns.append(positions)

    if args.csv:
        writer = csv.writer(args.csv)
        writer.writerow(["Title", "Text", "Left option", "Right option"] + parties)
        for question, positions in zip(scraped, position_columns):
            row = [question["title"]]
            row.extend(positions)
            row.extend([
                question["text"],
                question.get("left-option", ""),
                question.get("right-option", ""),
            ])
            writer.writerow(row)

    if args.print:
        print("Question".ljust(20) + " " + " ".join(party[:5].rjust(5) for party in parties))
        for question, positions in zip(scraped, position_columns):
            position_str = " ".join([str(pos if pos is not None else "N/A").rjust(5) for pos in positions])
            print(f"{question['title']:<20} {position_str}")
