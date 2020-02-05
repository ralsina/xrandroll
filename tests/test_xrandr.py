from xrandroll.xrandr import parse_data


def test_parse_data(test_data):
    data = test_data.read("sample_1.txt", deserialize=False).splitlines()
    screen = parse_data(data)
    assert len(screen.monitors) == 2
    assert [m.output for m in screen.monitors.values()] == ["eDP", "HDMI-A-0"]


def test_parse_with_disconnected_monitors(test_data):
    data = test_data.read("fisa_sample.txt", deserialize=False).splitlines()
    screen = parse_data(data)
    assert screen.choose_a_monitor() == "DP-1-1"


def test_replicated_monitors(test_data):
    data = test_data.read("replicated.txt", deserialize=False).splitlines()
    screen = parse_data(data)
    assert screen.monitors["eDP"].replica_of == ["HDMI-A-0"]
    assert screen.choose_a_monitor() == "eDP"
