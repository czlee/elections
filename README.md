# Scripts for collating NZ elections data

© Chuan-Zheng Lee 2014–2020

This is a collection of Python scripts that download and parse CSV files from the New Zealand Electoral Commission's results website, https://electionresults.govt.nz/. It produces aggregated statistics that aren't already presented in the statistics published by the Electoral Commission. In particular, it breaks down party vote distributions for special votes and overseas votes (which are not the same thing—overseas votes are a subset of special votes).

The main script is `analyse.py`. To see how to use it, run
```
python analyse.py --help
```
The `electorate.py` script provides the framework for collating statistics. The `download.py` script downloads results from the Commission website, which you can do separately, but the other two scripts should call it to download what they need as necessary. Downloading can take a while, because requests are spaced apart as a courtesy to the server, so please be patient the first time you run the script for an election.

I wrote most of this 2014, so it's designed to work for results from 1999 to 2014. The Commission changed its reporting format in 2017 to account for the much larger numbers of advance voters. I've done minimal modifications so that it doesn't crash with 2017 results, but it was more work to get it to collate ordinary advance votes in its own tally, so I haven't done that. So statistics that require a count of ordinary advance votes will be inaccurate.
