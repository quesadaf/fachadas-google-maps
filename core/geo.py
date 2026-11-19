from __future__ import annotations

import math


def point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    lat, lng = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        lati, lngi = polygon[i]
        latj, lngj = polygon[j]
        intersects = ((lngi > lng) != (lngj > lng)) and (
            lat < (latj - lati) * (lng - lngi) / ((lngj - lngi) or 1e-15) + lati
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def generate_grid_points(
    polygon: list[tuple[float, float]],
    spacing_m: int = 150,
    max_points: int = 120,
) -> list[tuple[float, float]]:
    if len(polygon) < 3:
        raise ValueError("El polígono requiere mínimo 3 puntos")

    lats = [p[0] for p in polygon]
    lngs = [p[1] for p in polygon]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)
    center_lat = sum(lats) / len(lats)

    lat_step = spacing_m / 111_320.0
    lon_m_per_degree = 111_320.0 * max(math.cos(math.radians(center_lat)), 0.1)
    lng_step = spacing_m / lon_m_per_degree

    points: list[tuple[float, float]] = []
    lat = min_lat
    while lat <= max_lat + 1e-12:
        lng = min_lng
        while lng <= max_lng + 1e-12:
            if point_in_polygon((lat, lng), polygon):
                points.append((round(lat, 7), round(lng, 7)))
                if len(points) >= max_points:
                    return points
            lng += lng_step
        lat += lat_step

    if not points:
        center = (sum(lats) / len(lats), sum(lngs) / len(lngs))
        if point_in_polygon(center, polygon):
            points.append((round(center[0], 7), round(center[1], 7)))

    return points
