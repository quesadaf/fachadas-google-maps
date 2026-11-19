from __future__ import annotations

import requests


COMMERCIAL_TYPES = [
    "store",
    "restaurant",
    "cafe",
    "bakery",
    "bar",
    "supermarket",
    "convenience_store",
    "clothing_store",
    "shoe_store",
    "electronics_store",
    "hardware_store",
    "home_goods_store",
    "furniture_store",
    "pharmacy",
    "beauty_salon",
    "hair_care",
    "spa",
    "gym",
    "car_repair",
    "car_dealer",
    "gas_station",
    "lodging",
    "bank",
    "real_estate_agency",
    "travel_agency",
]


class GooglePlacesClient:
    AGGREGATE_ENDPOINT = "https://areainsights.googleapis.com/v1:computeInsights"
    DETAILS_ENDPOINT = "https://places.googleapis.com/v1/places/{place_id}"

    DETAILS_FIELD_MASK = ",".join([
        "id",
        "displayName",
        "formattedAddress",
        "location",
        "primaryType",
        "types",
        "businessStatus",
        "websiteUri",
        "googleMapsUri",
    ])

    def __init__(self, api_key: str, timeout: int = 20):
        self.api_key = api_key
        self.timeout = timeout

    def places_in_polygon(self, polygon: list[tuple[float, float]]) -> tuple[int, list[str]]:
        coordinates = self._counter_clockwise_closed_polygon(polygon)
        payload = {
            "insights": ["INSIGHT_COUNT", "INSIGHT_PLACES"],
            "filter": {
                "locationFilter": {
                    "customArea": {
                        "polygon": {
                            "coordinates": [
                                {"latitude": lat, "longitude": lng}
                                for lat, lng in coordinates
                            ]
                        }
                    }
                },
                "typeFilter": {"includedTypes": COMMERCIAL_TYPES},
                "operatingStatus": ["OPERATING_STATUS_OPERATIONAL"],
            },
        }
        response = requests.post(
            self.AGGREGATE_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
            },
            timeout=self.timeout,
        )
        if not response.ok:
            raise RuntimeError(
                f"Places Aggregate HTTP {response.status_code}: {response.text[:700]}"
            )

        data = response.json()
        count = int(data.get("count", 0))
        ids: list[str] = []
        for item in data.get("placeInsights", []):
            value = item.get("place", "")
            if value.startswith("places/"):
                value = value.removeprefix("places/")
            if value:
                ids.append(value)
        return count, ids

    def place_details(self, place_id: str) -> dict:
        response = requests.get(
            self.DETAILS_ENDPOINT.format(place_id=place_id),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": self.DETAILS_FIELD_MASK,
            },
            params={"languageCode": "es", "regionCode": "CO"},
            timeout=self.timeout,
        )
        if not response.ok:
            raise RuntimeError(
                f"Place Details HTTP {response.status_code}: {response.text[:500]}"
            )
        return response.json()

    @staticmethod
    def _counter_clockwise_closed_polygon(
        polygon: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        points = list(polygon)
        if points[0] == points[-1]:
            points = points[:-1]

        # Shoelace usando x=lng, y=lat. Área positiva = CCW.
        signed = 0.0
        for i, (lat1, lng1) in enumerate(points):
            lat2, lng2 = points[(i + 1) % len(points)]
            signed += lng1 * lat2 - lng2 * lat1

        if signed < 0:
            points.reverse()

        points.append(points[0])
        return points
