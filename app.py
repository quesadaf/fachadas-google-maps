from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.geo import point_in_polygon
from core.google_places import GooglePlacesClient

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Fachadas Google Maps - Piloto", version="0.4.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class Point(BaseModel):
    lat: float
    lng: float


class AnalyzeRequest(BaseModel):
    polygon: list[Point] = Field(min_length=3)
    mode: Literal["count", "economic", "complete"] = "economic"


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


@app.post("/api/estimate")
def estimate(req: AnalyzeRequest) -> dict:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta GOOGLE_PLACES_API_KEY en .env")

    polygon = [(p.lat, p.lng) for p in req.polygon]
    client = GooglePlacesClient(api_key=api_key)

    try:
        count = client.count_in_polygon(polygon)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    detail_calls = 0 if req.mode == "count" else count
    cost_level = {
        "count": "Muy bajo",
        "economic": "Bajo / medio",
        "complete": "Medio / alto",
    }[req.mode]

    return {
        "count": count,
        "mode": req.mode,
        "estimated_detail_calls": detail_calls,
        "cost_level": cost_level,
        "note": (
            "Estimación orientativa. El consumo real depende de subdivisiones, "
            "cuotas gratuitas vigentes y campos solicitados."
        ),
    }


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta GOOGLE_PLACES_API_KEY en .env")

    polygon = [(p.lat, p.lng) for p in req.polygon]
    client = GooglePlacesClient(api_key=api_key)

    if req.mode == "count":
        try:
            count = client.count_in_polygon(polygon)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return {
            "count": count,
            "aggregate_count": count,
            "place_ids": [],
            "places": [],
            "id_file": None,
            "warning": "",
            "errors": [],
            "mode": req.mode,
        }

    try:
        original_count, place_ids, cells_used = client.place_ids_covering_polygon(polygon)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    raw_places, detail_errors = client.details_many(
        place_ids,
        complete=req.mode == "complete",
    )

    places: list[dict] = []
    kept_ids: list[str] = []

    for place in raw_places:
        loc = place.get("location") or {}
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if lat is None or lng is None:
            continue

        if not point_in_polygon((float(lat), float(lng)), polygon):
            continue

        place_id = place.get("id", "")
        if place_id:
            kept_ids.append(place_id)

        places.append({
            "place_id": place_id,
            "nombre": (place.get("displayName") or {}).get("text", ""),
            "direccion": place.get("formattedAddress", ""),
            "latitud": lat,
            "longitud": lng,
            "tipo_principal": place.get("primaryType", ""),
            "tipos": place.get("types", []),
            "estado": place.get("businessStatus", ""),
            "website": place.get("websiteUri", "") if req.mode == "complete" else "",
            "google_maps_url": place.get("googleMapsUri", ""),
            "fachada_comercial": "PENDIENTE_VISION",
            "aviso_comercial": "PENDIENTE_VISION",
            "vitrina": "PENDIENTE_VISION",
        })

    id_file = _save_place_ids(kept_ids)

    warning = ""
    if original_count > 100:
        warning = (
            f"El área contenía {original_count} comercios. "
            f"Se subdividió automáticamente en {cells_used} consultas de área "
            "y se eliminaron duplicados."
        )

    return {
        "count": len(places),
        "aggregate_count": original_count,
        "place_ids": kept_ids,
        "places": places,
        "id_file": id_file,
        "warning": warning,
        "errors": detail_errors[:20],
        "mode": req.mode,
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
