from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


COMMERCIAL_TYPES = [
    "store", "restaurant", "cafe", "bakery", "bar", "supermarket",
    "convenience_store", "clothing_store", "shoe_store", "electronics_store",
    "hardware_store", "home_goods_store", "furniture_store", "pharmacy",
    "beauty_salon", "hair_care", "spa", "gym", "car_repair", "car_dealer",
    "gas_station", "lodging", "bank", "real_estate_agency", "travel_agency",
]


class GooglePlacesClient:
    AGGREGATE_ENDPOINT = "https://areainsights.googleapis.com/v1:computeInsights"
    DETAILS_ENDPOINT = "https://places.googleapis.com/v1/places/{place_id}"

    BASIC_FIELDS = [
        "id", "displayName", "formattedAddress", "location",
        "primaryType", "types", "businessStatus", "googleMapsUri",
    ]
    COMPLETE_FIELDS = BASIC_FIELDS + ["websiteUri"]

    def __init__(self, api_key: str, timeout: int = 20, workers: int = 12):
        self.api_key = api_key
        self.timeout = timeout
        self.workers = workers

    def count_in_polygon(self, polygon: list[tuple[float, float]]) -> int:
        data = self._aggregate_request(polygon, ["INSIGHT_COUNT"])
        return int(data.get("count", 0))

    def place_ids_in_polygon(self, polygon: list[tuple[float, float]]) -> list[str]:
        data = self._aggregate_request(polygon, ["INSIGHT_PLACES"])
        ids: list[str] = []
        for item in data.get("placeInsights", []):
            value = item.get("place", "")
            if value.startswith("places/"):
                value = value.removeprefix("places/")
            if value:
                ids.append(value)
        return ids

    def place_ids_covering_polygon(
        self,
        polygon: list[tuple[float, float]],
        max_depth: int = 6,
    ) -> tuple[int, list[str], int]:
        original_count = self.count_in_polygon(polygon)
        if original_count <= 100:
            return original_count, self.place_ids_in_polygon(polygon), 1

        min_lat = min(p[0] for p in polygon)
        max_lat = max(p[0] for p in polygon)
        min_lng = min(p[1] for p in polygon)
        max_lng = max(p[1] for p in polygon)

        root = self._rect_polygon(min_lat, min_lng, max_lat, max_lng)
        ids: set[str] = set()
        cells_used = 0

        def walk(cell: list[tuple[float, float]], depth: int) -> None:
            nonlocal cells_used
            count = self.count_in_polygon(cell)
            cells_used += 1

            if count == 0:
                return

            if count <= 100:
                ids.update(self.place_ids_in_polygon(cell))
                return

            if depth >= max_depth:
                raise RuntimeError(
                    "Una subzona todavía supera 100 lugares. "
                    "Reduce el perímetro o aumenta max_depth."
                )

            for child in self._split_rect(cell):
                walk(child, depth + 1)

        walk(root, 0)
        return original_count, sorted(ids), cells_used

    def details_many(self, place_ids: list[str], complete: bool = False) -> tuple[list[dict], list[str]]:
        results: list[dict] = []
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            future_map = {
                pool.submit(self.place_details, place_id, complete): place_id
                for place_id in place_ids
            }
            for future in as_completed(future_map):
                place_id = future_map[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    errors.append(f"{place_id}: {exc}")

        return results, errors

    def place_details(self, place_id: str, complete: bool = False) -> dict:
        field_mask = ",".join(self.COMPLETE_FIELDS if complete else self.BASIC_FIELDS)
        response = requests.get(
            self.DETAILS_ENDPOINT.format(place_id=place_id),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": field_mask,
            },
            params={"languageCode": "es", "regionCode": "CO"},
            timeout=self.timeout,
        )
        if not response.ok:
            raise RuntimeError(
                f"Place Details HTTP {response.status_code}: {response.text[:500]}"
            )
        return response.json()

    def _aggregate_request(
        self,
        polygon: list[tuple[float, float]],
        insights: list[str],
    ) -> dict:
        coordinates = self._counter_clockwise_closed_polygon(polygon)
        payload = {
            "insights": insights,
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
        return response.json()

    @staticmethod
    def _rect_polygon(
        min_lat: float, min_lng: float, max_lat: float, max_lng: float
    ) -> list[tuple[float, float]]:
        return [
            (min_lat, min_lng),
            (min_lat, max_lng),
            (max_lat, max_lng),
            (max_lat, min_lng),
        ]

    @classmethod
    def _split_rect(
        cls, polygon: list[tuple[float, float]]
    ) -> list[list[tuple[float, float]]]:
        min_lat = min(p[0] for p in polygon)
        max_lat = max(p[0] for p in polygon)
        min_lng = min(p[1] for p in polygon)
        max_lng = max(p[1] for p in polygon)
        mid_lat = (min_lat + max_lat) / 2
        mid_lng = (min_lng + max_lng) / 2

        return [
            cls._rect_polygon(min_lat, min_lng, mid_lat, mid_lng),
            cls._rect_polygon(min_lat, mid_lng, mid_lat, max_lng),
            cls._rect_polygon(mid_lat, min_lng, max_lat, mid_lng),
            cls._rect_polygon(mid_lat, mid_lng, max_lat, max_lng),
        ]

    @staticmethod
    def _counter_clockwise_closed_polygon(
        polygon: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        points = list(polygon)
        if points[0] == points[-1]:
            points = points[:-1]

        signed = 0.0
        for i, (lat1, lng1) in enumerate(points):
            lat2, lng2 = points[(i + 1) % len(points)]
            signed += lng1 * lat2 - lng2 * lat1

        if signed < 0:
            points.reverse()

        points.append(points[0])
        return points
