"""Web server for the rotation explorer.

Run:   python server.py
Open:  http://localhost:8000
"""
import math
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analysis import analyse
from crops import CROPS
from sites import SITES

app = FastAPI(title="Rotation Explorer")

DEFAULT_ROTATIONS = {
    2: ["winter_wheat", "fallow"],
    3: ["winter_wheat", "spring_wheat", "fallow"],
    4: ["winter_wheat", "canola", "winter_wheat", "fallow"],
}


class Request(BaseModel):
    lat: float
    lon: float
    rotation: list[str]
    soil_ph: float | None = None
    weights: dict[str, float]


def clean(value):
    """Turn pandas/numpy values into plain JSON-friendly Python values."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "item"):          # numpy numbers
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


@app.get("/api/options")
def options():
    return {
        "sites": [{"name": name, "lat": lat, "lon": lon} for name, (lat, lon) in SITES.items()],
        "crops": [{"key": key, "name": info["name"]} for key, info in CROPS.items()],
        "default_rotations": DEFAULT_ROTATIONS,
    }


@app.post("/api/analyse")
def run_analysis(request: Request):
    unknown = [c for c in request.rotation if c not in CROPS]
    if unknown or not 2 <= len(request.rotation) <= 4:
        raise HTTPException(400, "Rotation must have 2-4 known crops.")
    try:
        result = analyse(request.lat, request.lon, request.rotation,
                         request.soil_ph, request.weights)
    except Exception as error:
        raise HTTPException(502, f"Could not get data for this field: {error}")
    return clean(result)


STATIC = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
