"""Read/Write system display state using xrandr."""

import subprocess

from .monitor import Monitor, _split_by_lines_matching


def is_replica_of(a, b):
    """Return True if monitor a is a replica of b.

    Replica means same resolution and position.
    """
    return (
        a.pos_x == b.pos_x
        and a.pos_y == b.pos_y
        and a.res_x == b.res_x
        and a.res_y == b.res_y
        and b.enabled
    )


class Screen:
    """A Screen is a collection of monitors."""

    def __init__(self, data):
        self.monitors = {}
        for monitor_data in _split_by_lines_matching(r"^[^ \t].*", data[1:]):
            m = Monitor(monitor_data)
            self.monitors[m.output] = m
        self.update_replica_of()

    def update_replica_of(self):
        """Decide which monitors are replicas of each other and
        mark them as such."""
        for a in self.monitors:
            self.monitors[a].replica_of = []
            for b in self.monitors:
                if a != b and is_replica_of(self.monitors[a], self.monitors[b]):
                    self.monitors[a].replica_of.append(b)

    def choose_a_monitor(self):
        """Choose what monitor to select by default.

        * Not disabled
        * Primary, if possible
        """

        candidate = None
        for name, mon in self.monitors.items():
            if not mon.enabled:
                continue
            if mon.primary:
                return name
            candidate = name
        return candidate


def read_data():
    data = subprocess.check_output(
        ["xrandr", "--verbose"], encoding="utf-8"
    ).splitlines()
    return data


def parse_data(data):
    # Going to pretend there can only be one screen because life is short.
    return Screen(_split_by_lines_matching("^Screen ", data)[0])
