"""Downloads polling place results files from the New Zealand Electoral Commission website.

Chuan-Zheng Lee <czlee@stanford.edu>
November 2014
"""
import urllib
import os
from config import NUM_ELECTORATES, ELECTORATE_NAMES_1999

URL_GENERAL = "http://electionresults.govt.nz/electionresults_{year:d}/e9/csv/e9_part8_{type:s}_{elec_id:d}.csv"
URL_1999 = "http://electionresults.govt.nz/electionresults_{year:d}/e9/csv/{elec_id:02d}_{elec_name:s}_{type:s}.csv"
RESULTS_DIR = "results"

def check_directories(year):
    """Checks if the directory for this year exists and creates it if it doesn't."""
    if hasattr(check_directories, "checked"):
        return
    check_directories.checked = True
    if os.path.exists(RESULTS_DIR) and not os.path.isdir(RESULTS_DIR):
        raise IOError("'{0}' is not a directory".format(RESULTS_DIR))
    dirname = os.path.join(RESULTS_DIR, str(year))
    if os.path.exists(dirname) and not os.path.isdir(dirname):
        raise IOError("'{0}' is not a directory".format(dirname))
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def get_filename(year, elec_id, type):
    """Returns the filename for this year and electorate."""
    return os.path.join(RESULTS_DIR, str(year), "electorate_{elec_id:d}_{type:s}.csv".format(elec_id=elec_id, type=type))

def download_all_polling_place_results(year, types=["party"], force=False, quiet=False):
    """Downloads all CSV files for the year."""
    for elec_id in range(1, NUM_ELECTORATES[year]+1):
        for type in types:
            download_polling_place_results(year, elec_id, type, force, quiet)

def get_details_file_url(year, elec_id, type):
    if year == 1999:
        return URL_1999.format(year=year, elec_id=elec_id,
                elec_name=ELECTORATE_NAMES_1999[elec_id-1], type=type[0])
    return URL_GENERAL.format(year=year, elec_id=elec_id, type=type)

def download_polling_place_results(year, elec_id, type="party", force=False, quiet=False):
    """Downloads the CSV file for an electorate and vote type and returns the
    name of the local copy of the file."""
    check_directories(year)
    url = get_details_file_url(year, elec_id, type)
    filename = get_filename(year, elec_id, type)
    if os.path.exists(filename) and not force:
        if not quiet:
            print("'{0}' already exists, not downloading".format(filename))
    else:
        urllib.urlretrieve(url, filename)
    return filename

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int)
    parser.add_argument("electorate", nargs="?", type=int, default=None)
    parser.add_argument("type", nargs="?", type=str, default="party")
    parser.add_argument("-f", "--force", action="store_true")
    args = parser.parse_args()

    if args.electorate is None:
        download_all_polling_place_results(args.year, force=args.force)
    else:
        download_polling_place_results(args.year, args.electorate, args.type, args.force)
