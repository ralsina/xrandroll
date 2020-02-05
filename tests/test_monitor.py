from xrandroll.monitor import Monitor

BASIC_HEADER = "eDP connected primary 1920x1080+0+1080 (0x56) normal (normal left inverted right x axis y axis) 309mm x 173mm"  # noqa


def test_parse_pos():
    data = [BASIC_HEADER]
    m = Monitor(data)
    assert m.pos_x == 0
    assert m.pos_y == 1080


def test_parse_output():
    data = [BASIC_HEADER]
    m = Monitor(data)
    assert m.output == "eDP"


def test_parse_modes(test_data):
    data = test_data.read("monitor_1.txt", deserialize=False).splitlines()
    m = Monitor(data)
    assert len(m.modes) == 9