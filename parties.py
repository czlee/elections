"""Links parties across elections using party_names.toml.

party_names.toml has one table per party, keyed by a stable party_id, with a
short_name for display. Under it, each election year gives the name (or list
of names) the party appears under in that election's data, and `part_of`
gives, for each year, the party_id of an umbrella party whose votes included
this party's (e.g. Vision New Zealand was part of Freedoms NZ in 2023).

Every name in the data must be in the file, so a new election makes you decide
explicitly how its parties link to earlier ones.
"""
import re
import tomllib
from collections import Counter

PARTY_NAMES_FILE = "party_names.toml"


class PartyNames:

    def __init__(self, filename=PARTY_NAMES_FILE):
        self.filename = filename
        self.ids = {}       # (election, name) -> party_id
        self.part_of = {}   # (election, party_id) -> umbrella party_id
        self.short_names = {}  # party_id -> short name, for display
        with open(filename, "rb") as f:
            data = tomllib.load(f)
        for party_id, entry in data.items():
            if "short_name" not in entry:
                raise ValueError("{0}: no short_name in {1}".format(party_id, filename))
            for key, value in entry.items():
                if key == "short_name":
                    self.short_names[party_id] = value
                elif key == "part_of":
                    for election, umbrella in value.items():
                        if umbrella not in data:
                            raise ValueError("{0}: unknown part_of party {1!r}".format(party_id, umbrella))
                        self.part_of[(election, party_id)] = umbrella
                elif re.fullmatch(r"\d{4}", key):
                    for name in [value] if isinstance(value, str) else value:
                        if (key, name) in self.ids:
                            raise ValueError("{0!r} ({1}) is listed under both {2} and {3}".format(
                                name, key, self.ids[(key, name)], party_id))
                        self.ids[(key, name)] = party_id
                else:
                    raise ValueError("{0}: unknown key {1!r} in {2}".format(party_id, key, filename))

    def party_id(self, election, name):
        try:
            return self.ids[(election, name)]
        except KeyError:
            raise KeyError("{0!r} ({1}) isn't in {2}".format(name, election, self.filename)) from None

    def to_ids(self, election, totals):
        """Converts {name: votes} to {party_id: votes}."""
        result = Counter()
        for name, votes in totals.items():
            result[self.party_id(election, name)] += votes
        return result

    def counterpart(self, party_id, election, totals):
        """Returns the party_id in `election` to compare `party_id` with: itself
        if it has votes in `totals` (that election's {party_id: votes}), else
        the umbrella party it was part of, else None."""
        if party_id in totals:
            return party_id
        umbrella = self.part_of.get((election, party_id))
        if umbrella in totals:
            return umbrella
        return None
