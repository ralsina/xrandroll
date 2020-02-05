"""Read/Write system display state using xrandr."""

import subprocess

from .monitor import Monitor, _split_by_lines_matching


class Screen:
    """A Screen is a collection of monitors."""

    def __init__(self, data):
        self.monitors = {}
        for monitor_data in _split_by_lines_matching(r"^[^ \t].*", data[1:]):
            m = Monitor(monitor_data)
            self.monitors[m.output] = m


def read_data():
    data = subprocess.check_output(
        ["xrandr", "--verbose"], encoding="utf-8"
    ).splitlines()
    return data


def parse_data(data):
    # Going to pretend there can only be one screen because life is short.
    return Screen(_split_by_lines_matching("^Screen ", data)[0])
