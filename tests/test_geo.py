from core.geo import generate_grid_points, point_in_polygon


def test_point_in_polygon():
    poly = [(4.0, -74.0), (4.0, -73.99), (4.01, -73.99), (4.01, -74.0)]
    assert point_in_polygon((4.005, -73.995), poly)
    assert not point_in_polygon((4.02, -73.995), poly)


def test_generate_grid_points():
    poly = [(4.0, -74.0), (4.0, -73.995), (4.005, -73.995), (4.005, -74.0)]
    pts = generate_grid_points(poly, spacing_m=100, max_points=100)
    assert pts
    assert len(pts) <= 100
    assert all(point_in_polygon(p, poly) for p in pts)
