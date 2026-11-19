from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.google_places import GooglePlacesClient

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Fachadas Google Maps - Piloto", version="0.2.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class Point(BaseModel):
    lat: float
    lng: float


class AnalyzeRequest(BaseModel):
    polygon: list[Point] = Field(min_length=3)


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
        raise HTTPException(
            status_code=500,
            detail="Falta GOOGLE_PLACES_API_KEY en el archivo .env",
        )

    polygon = [(p.lat, p.lng) for p in req.polygon]
    client = GooglePlacesClient(api_key=api_key)

    try:
        count, place_ids = client.places_in_polygon(polygon)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if count > 100 and not place_ids:
        return {
            "count": count,
            "place_ids": [],
            "places": [],
            "id_file": None,
            "warning": (
                "El polígono contiene más de 100 comercios. "
                "Google Places Aggregate no devuelve Place IDs en ese caso. "
                "Reduce el perímetro y vuelve a intentar."
            ),
        }

    places: list[dict] = []
    errors: list[str] = []
    for place_id in place_ids:
        try:
            place = client.place_details(place_id)
            places.append({
                "place_id": place_id,
                "nombre": (place.get("displayName") or {}).get("text", ""),
                "direccion": place.get("formattedAddress", ""),
                "latitud": (place.get("location") or {}).get("latitude"),
                "longitud": (place.get("location") or {}).get("longitude"),
                "tipo_principal": place.get("primaryType", ""),
                "tipos": place.get("types", []),
                "estado": place.get("businessStatus", ""),
                "website": place.get("websiteUri", ""),
                "google_maps_url": place.get("googleMapsUri", ""),
                "fachada_comercial": "PENDIENTE_VISION",
                "aviso_comercial": "PENDIENTE_VISION",
                "vitrina": "PENDIENTE_VISION",
            })
        except Exception as exc:
            errors.append(f"{place_id}: {exc}")

    id_file = _save_place_ids(place_ids)

    return {
        "count": count,
        "place_ids": place_ids,
        "places": places,
        "id_file": id_file,
        "warning": "",
        "errors": errors[:20],
        "storage_notice": (
            "La interfaz muestra datos de Places en vivo. "
            "El archivo persistente guarda únicamente Place IDs, "
            "no nombres ni direcciones de Google."
        ),
    }


def _save_place_ids(place_ids: list[str]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"place_ids_{stamp}.csv"
    path = OUTPUT_DIR / filename
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["place_id", "captured_at_utc"])
        writer.writeheader()
        now = datetime.now(timezone.utc).isoformat()
        for place_id in place_ids:
            writer.writerow({"place_id": place_id, "captured_at_utc": now})
    return filename


@app.get("/api/download/{filename}")
def download(filename: str) -> FileResponse:
    safe = Path(filename).name
    path = OUTPUT_DIR / safe
    if not path.exists() or not safe.startswith("place_ids_") or path.suffix.lower() != ".csv":
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="text/csv", filename=safe)
