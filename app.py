from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.geo import generate_grid_points, point_in_polygon
from core.google_places import GooglePlacesClient

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Fachadas Google Maps - Piloto", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class Point(BaseModel):
    lat: float
    lng: float


class AnalyzeRequest(BaseModel):
    polygon: list[Point] = Field(min_length=3)
    grid_spacing_m: int = Field(default=150, ge=50, le=500)
    search_radius_m: int = Field(default=120, ge=50, le=500)
    max_grid_points: int = Field(default=120, ge=1, le=500)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
def config() -> dict:
    return {
        "googleMapsBrowserApiKey": os.getenv("GOOGLE_MAPS_BROWSER_API_KEY", ""),
        "defaultCenter": {"lat": 4.6486, "lng": -74.0779},
        "defaultZoom": 13,
    }


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta GOOGLE_PLACES_API_KEY en el archivo .env")

    polygon = [(p.lat, p.lng) for p in req.polygon]
    grid_points = generate_grid_points(
        polygon,
        spacing_m=req.grid_spacing_m,
        max_points=req.max_grid_points,
    )

    client = GooglePlacesClient(api_key=api_key)
    by_id: dict[str, dict] = {}
    errors: list[str] = []

    for lat, lng in grid_points:
        try:
            for place in client.search_nearby(lat, lng, radius_m=req.search_radius_m):
                loc = place.get("location") or {}
                plat = loc.get("latitude")
                plng = loc.get("longitude")
                if plat is None or plng is None:
                    continue
                if not point_in_polygon((float(plat), float(plng)), polygon):
                    continue

                place_id = place.get("id")
                if not place_id:
                    continue

                display_name = (place.get("displayName") or {}).get("text", "")
                primary_type = place.get("primaryType", "")
                types = place.get("types", [])

                excluded = {
                    "country", "administrative_area_level_1", "administrative_area_level_2",
                    "locality", "sublocality", "neighborhood", "postal_code", "route",
                    "street_address", "intersection", "political", "school", "university",
                    "hospital", "police", "fire_station", "courthouse", "city_hall",
                    "place_of_worship", "cemetery", "park",
                }
                if primary_type in excluded:
                    continue

                by_id[place_id] = {
                    "place_id": place_id,
                    "nombre": display_name,
                    "direccion": place.get("formattedAddress", ""),
                    "latitud": plat,
                    "longitud": plng,
                    "tipo_principal": primary_type,
                    "tipos": ", ".join(types),
                    "estado": place.get("businessStatus", ""),
                    "website": place.get("websiteUri", ""),
                    "google_maps_url": place.get("googleMapsUri", ""),
                    "fachada_comercial": "PENDIENTE_VISION",
                    "aviso_comercial": "PENDIENTE_VISION",
                    "vitrina": "PENDIENTE_VISION",
                    "nombre_ocr": "",
                    "confianza_vision": "",
                }
        except Exception as exc:
            errors.append(f"Punto {lat:.6f},{lng:.6f}: {exc}")

    places = sorted(by_id.values(), key=lambda p: (p["direccion"], p["nombre"]))
    csv_name = _save_csv(places)

    return {
        "grid_points": [{"lat": lat, "lng": lng} for lat, lng in grid_points],
        "places": places,
        "count": len(places),
        "csv_file": csv_name,
        "errors": errors[:20],
    }


def _save_csv(rows: list[dict]) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"negocios_{stamp}.csv"
    path = OUTPUT_DIR / filename
    fieldnames = [
        "place_id", "nombre", "direccion", "latitud", "longitud",
        "tipo_principal", "tipos", "estado", "website", "google_maps_url",
        "fachada_comercial", "aviso_comercial", "vitrina", "nombre_ocr", "confianza_vision",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return filename


@app.get("/api/download/{filename}")
def download(filename: str) -> FileResponse:
    safe = Path(filename).name
    path = OUTPUT_DIR / safe
    if not path.exists() or path.suffix.lower() != ".csv":
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="text/csv", filename=safe)
