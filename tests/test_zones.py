from cctv_ai.zones import Zone


def test_zone_contains_point_inside_polygon():
    zone = Zone([(0, 0), (10, 0), (10, 10), (0, 10)])

    assert zone.contains((5, 5))


def test_zone_rejects_point_outside_polygon():
    zone = Zone([(0, 0), (10, 0), (10, 10), (0, 10)])

    assert not zone.contains((12, 5))


def test_zone_normalizes_pixel_coordinates():
    zone = Zone([(20, 10), (80, 10), (80, 90), (20, 90)])

    assert zone.to_normalized(100, 100).points == [(0.2, 0.1), (0.8, 0.1), (0.8, 0.9), (0.2, 0.9)]

