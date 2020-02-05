"""Read/Write system display state using xrandr."""

import subprocess


def read_data():
    data = subprocess.check_output(["xrandr", "--verbose"])
    return data


def parse_data(data):
    print(data)


if __name__ == "__main__":
    print(parse_data(read_data()))
