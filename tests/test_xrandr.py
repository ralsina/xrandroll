from xrandroll.xrandr import parse_data


def test_parse_data(test_data):
    data = test_data.read("sample_1.txt", deserialize=False).splitlines()
    monitors = parse_data(data)
    assert len(monitors) == 2
    assert [m.output for m in monitors] == ["eDP", "HDMI-A-0"]


def test_parse_with_disconnected_monitors(test_data):
    data = test_data.read("fisa_sample.txt", deserialize=False).splitlines()
    parse_data(data)
