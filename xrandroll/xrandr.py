"""Read/Write system display state using xrandr."""

import subprocess

from monitor import Monitor, _split_by_lines_matching


def read_data():
    data = subprocess.check_output(
        ["xrandr", "--verbose"], encoding="utf-8"
    ).splitlines()
    return data


def parse_data(data):
    # Going to pretend there can only be one screen because life is short.
    screen = _split_by_lines_matching("^Screen ", data)[0]

    result = []
    for monitor_data in _split_by_lines_matching(r"^[^ \t].*", screen[1:]):
        result.append(Monitor(monitor_data))
    return result


if __name__ == "__main__":
    print(parse_data(read_data()))
