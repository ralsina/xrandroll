"""An object that represents a monitor."""

import re

import parse


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
    """One of the modes for a monitor.

    Note:

    mode.name is the hex thing, like "0x56", not "1920x1080"
    """

    def __init__(self, data):
        """Initialize Mode from xrandr data."""
        self.data = data
        self.header = data[0]
        self.name = parse.search("({mode_name})", self.header)["mode_name"]
        self.res_x = parse.search("h: width {res_x:d}", data[1])["res_x"]
        self.res_y = parse.search("v: height {res_y:d}", data[2])["res_y"]
        self.refresh = parse.search("{refresh:f}Hz", data[2])["refresh"]
        self.preferred = "+preferred" in self.header
        self.current = "*current" in self.header

    def __repr__(self):
        return self.header.strip()


class Monitor:
    """Object representing a monitor according to xrandr."""

    def __init__(self, data):
        """Initialize a monitor object out of data from xrandr --verbose.

        data is a list of lines.
        """

        self.header = data.pop(0)
        self.pos_x, self.pos_y = parse.search("+{:d}+{:d}", self.header)
        modes_data = _split_by_lines_matching("^  [^ ]", data)
        fields_data = _split_by_lines_matching(r"^\t[^ ]", modes_data.pop(0))

        self.modes = {}
        for m in (Mode(d) for d in modes_data):
            self.modes[m.name] = m

        self.fields = {}
        for f in (Field(d) for d in fields_data):
            self.fields[f.name] = f

    def get_current_mode_name(self):
        for k, v in self.modes.values():
            if v.current:
                return k

    def set_current_mode(self, mode_name):
        for k, v in self.modes.items():
            v.current = k == mode_name
