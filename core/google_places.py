from __future__ import annotations

import requests


class GooglePlacesClient:
    ENDPOINT = "https://places.googleapis.com/v1/places:searchNearby"
    FIELD_MASK = ",".join([
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.primaryType",
        "places.types",
        "places.businessStatus",
        "places.websiteUri",
        "places.googleMapsUri",
    ])

    def __init__(self, api_key: str, timeout: int = 20):
        self.api_key = api_key
        self.timeout = timeout

    def search_nearby(self, lat: float, lng: float, radius_m: int = 120) -> list[dict]:
        payload = {
            "maxResultCount": 20,
            "rankPreference": "DISTANCE",
            "languageCode": "es",
            "regionCode": "CO",
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m),
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": self.FIELD_MASK,
        }
        response = requests.post(self.ENDPOINT, json=payload, headers=headers, timeout=self.timeout)
        if not response.ok:
            raise RuntimeError(
                f"Google Places HTTP {response.status_code}: {response.text[:500]}"
            )
        return response.json().get("places", [])
