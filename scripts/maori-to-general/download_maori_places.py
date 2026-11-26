"""Downloads the 2026 preliminary per-voting-place files for the Māori
electorates (65-71), for maori_to_general.py, into
data/elections/2026-prelim/raw/eNN/votingplaces/. Skips files already there. Run it
from the repository root.
"""
import os
import re
import time
import urllib.request

BASE = "https://www.electionresults.govt.nz/electionresults_2026_preliminary/xml/"
RAWDIR = "data/elections/2026-prelim/raw"
MAORI = range(65, 72)
USER_AGENT = "Elections Analysis"  # Python's default is blocked (NOTES.md)
DELAY = 0.4


def get(path):
    request = urllib.request.Request(BASE + path, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response:
        content = response.read()
    time.sleep(DELAY)
    return content


def main():
    top = os.path.join(RAWDIR, "votingplaces.xml")
    if not os.path.exists(top):
        with open(top, "wb") as f:
            f.write(get("votingplaces.xml"))
    for e in MAORI:
        subdir = "e{0:02d}/votingplaces/".format(e)
        listing = get(subdir).decode("utf-8")
        names = re.findall(r'href="({0:02d}-\d+\.xml)"'.format(e), listing)
        os.makedirs(os.path.join(RAWDIR, subdir), exist_ok=True)
        new = 0
        for name in names:
            filename = os.path.join(RAWDIR, subdir, name)
            if not os.path.exists(filename):
                with open(filename, "wb") as f:
                    f.write(get(subdir + name))
                new += 1
        print("e{0:02d}: {1} files, {2} downloaded".format(e, len(names), new), flush=True)


if __name__ == "__main__":
    main()
