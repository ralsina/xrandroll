"""An object that represents a monitor."""

import re

import parse


def _split_by_lines_matching(pattern, lines):
    """Return a list of groups of lines, splitting on lines
    matching the pattern. The line matching the pattern is
    included in the SECOND group. Empty groups are removed."""
    groups = [[]]
    for line in lines:
        if re.match(pattern, line):  # Start a new group
            groups.append([])
        groups[-1].append(line)

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
        self.res_x = parse.search("h: width{:s}{res_x:d}", data[1])["res_x"]
        self.res_y = parse.search("v: height{:s}{res_y:d}", data[2])["res_y"]
        self.refresh = parse.search("{refresh:f}Hz", data[2])["refresh"]
        self.preferred = "+preferred" in self.header
        self.current = "*current" in self.header
        self.frequency = parse.search("{freq:f}Hz", data[2])["freq"]

    def __repr__(self):
        return self.header.strip()

    def __str__(self):
        return f"{self.res_x}x{self.res_y} {int(self.frequency)}Hz ({self.name})"


class Monitor:
    """Object representing a monitor according to xrandr."""

    res_x = 0
    res_y = 0
    pos_x = 0
    pos_y = 0
    enabled = False
    primary = False
    orientation = "normal"
    item = None
    w_in_mm = 100
    h_in_mm = 100

    def __init__(self, data):
        """Initialize a monitor object out of data from xrandr --verbose.

        data is a list of lines.
        """

        self.header = data.pop(0)
        self.output = parse.search("{}{:s}", self.header)[0]
        self.primary = "primary" in self.header
        self.replica_of = []
        if "disconnected" in self.header:
            # No modes, no pos, no fields, no nothing.
            return
        self.enabled = "+" in self.header
        if self.enabled:
            self.pos_x, self.pos_y = parse.search("+{:d}+{:d}", self.header)
            self.res_x, self.res_y = parse.search("{:d}x{:d}", self.header)
            self.w_in_mm, self.h_in_mm = parse.search("{:d}mm x {:d}mm", self.header)
        self.orientation = parse.search("{:w} (normal left inverted", self.header)[0]

        modes_data = _split_by_lines_matching("^  [^ ]", data)
        if modes_data:
            fields_data = _split_by_lines_matching(r"^\t[^ ]", modes_data.pop(0))
        else:
            fields_data = []

        self.modes = {}
        for m in (Mode(d) for d in modes_data):
            self.modes[m.name] = m

        self.fields = {}
        for f in (Field(d) for d in fields_data):
            self.fields[f.name] = f

    def __repr__(self):
        return f"Monitor: {self.output}"

    def get_matching_mode(self, mode):
        """Try to find a mode that matches resolution with given one."""
        for m in self.modes.values():
            if m.res_x == mode.res_x and m.res_y == mode.res_y:
                return m

    def get_current_mode_name(self):
        for k, v in self.modes.items():
            if v.current:
                return k
        return None

    def get_current_mode(self):
        for k, v in self.modes.items():
            if v.current:
                return v
        return None

    def set_current_mode(self, mode_name):
        for k, v in self.modes.items():
            v.current = k == mode_name

    def get_preferred_mode(self):
        for k, v in self.modes.items():
            if v.preferred:
                return v
        return None

    def guess_scale_mode(self):
        """Given a monitor's data, try to guess what scaling
        mode it's using.

        TODO: detect "Automatic: physical dimensions"
        """
        if not self.enabled:
            return None
        mode = self.get_current_mode()
        scale_x = self.res_x / mode.res_x
        scale_y = self.res_y / mode.res_y

        if 1 == scale_x == scale_y:
            print("Scale mode looks like 1x1")
            return "Disabled (1x1)"
        elif scale_x == scale_y:
            print("Looks like Manual, same in both dimensions")
            return "Manual, same in both dimensions"
        else:
            return "Manual"
