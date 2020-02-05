from xrandroll.monitor import Monitor


def test_parse_pos():
    data = [
        "eDP connected primary 1920x1080+0+1080 (0x56) normal (normal left inverted right x axis y axis) 309mm x 173mm"
    ]
    m = Monitor(data)
    assert m.pos_x == 0
    assert m.pos_y == 1080
