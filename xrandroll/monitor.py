"""An object that represents a monitor."""

import re


def _split_by_lines_matching(pattern, lines):
    """Return a list of groups of lines, splitting on lines
    matching the pattern. The line matching the pattern is
    included in the SECOND group. Empty groups are removed."""
    groups = [[]]
    for l in lines:
        if re.match(pattern, l):  # Start a new group
            groups.append([])
        groups[-1].append(l)

    return [g for g in groups if g]


class Field:
    """One of the data fields for a monitor."""

    def __init__(self, data):
        """Initialize Field from xrandr data."""
        self.name = data[0].split(":")[0].strip()
        self.value = data[:]

    def __repr__(self):
        return f"{self.name}: {self.value}"


class Mode:
    """One of the modes for a monitor."""

    def __init__(self, data):
        """Initialize Mode from xrandr data."""
        self.data = data
        self.name = data[0].strip().split()[0]

    def __repr__(self):
        return self.data[0].strip()


class Monitor:
    """Object representing a monitor according to xrandr."""

    def __init__(self, data):
        """Initialize a monitor object out of data from xrandr --verbose.

        data is a list of lines.
        """

        _ = data.pop(0)
        modes_data = _split_by_lines_matching("^  [^ ]", data)
        fields_data = _split_by_lines_matching(r"^\t[^ ]", modes_data.pop(0))

        self.modes = {}
        for m in (Mode(d) for d in modes_data):
            self.modes[m.name] = m

        self.fields = {}
        for f in (Field(d) for d in fields_data):
            self.fields[f.name] = f
