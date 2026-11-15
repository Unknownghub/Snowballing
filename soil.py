"""Step 7: soil at a point from the USDA soil survey (Soil Data Access)."""
import json
import os

import requests

URL = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
CACHE_DIR = "cache"

QUERY = """
SELECT mu.mukey, mu.muname, c.compname, c.comppct_r, c.majcompflag, c.slope_r,
       ch.hzdept_r, ch.hzdepb_r, ch.claytotal_r, ch.om_r, ch.ph1to1h2o_r, ch.kwfact
FROM mapunit mu
LEFT JOIN component c ON c.mukey = mu.mukey
LEFT JOIN chorizon ch ON ch.cokey = c.cokey
WHERE mu.mukey IN (
    SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({lon} {lat})')
)
ORDER BY c.comppct_r DESC, ch.hzdept_r
"""


def to_number(text):
    """The survey sends numbers as text; empty or missing becomes None."""
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def fetch_rows(lat, lon):
    """Raw rows from the survey, as a list of dictionaries. Saved to cache."""
    cache_file = os.path.join(CACHE_DIR, f"soil_{lat:.4f}_{lon:.4f}.json")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    query = QUERY.format(lat=lat, lon=lon)
    response = requests.post(URL, data={"query": query, "format": "JSON+COLUMNNAME"}, timeout=60)
    response.raise_for_status()
    table = response.json().get("Table", [])
    if len(table) < 2:
        rows = []
    else:
        names, values = table[0], table[1:]
        rows = [dict(zip(names, row)) for row in values]

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_file, "w") as f:
        json.dump(rows, f)
    return rows


def summarise(rows):
    """Main soil type at the point and its surface layer."""
    if not rows:
        return None
    main = max(rows, key=lambda r: to_number(r["comppct_r"]) or 0)
    layers = [r for r in rows if r["compname"] == main["compname"]]
    surface = min(layers, key=lambda r: to_number(r["hzdept_r"]) if to_number(r["hzdept_r"]) is not None else 999)
    return {
        "map_unit": main["muname"],
        "soil": main["compname"],
        "share_pct": to_number(main["comppct_r"]),
        "slope_pct": to_number(main["slope_r"]),
        "surface_depth_cm": (to_number(surface["hzdept_r"]), to_number(surface["hzdepb_r"])),
        "clay_pct": to_number(surface["claytotal_r"]),
        "organic_matter_pct": to_number(surface["om_r"]),
        "survey_ph": to_number(surface["ph1to1h2o_r"]),
        "erodibility_k": to_number(surface["kwfact"]),
        "source": "USDA NRCS soil survey (SSURGO) via Soil Data Access",
    }


def get_soil(lat, lon):
    return summarise(fetch_rows(lat, lon))


if __name__ == "__main__":
    for name, (lat, lon) in {
        "Ritzville": (47.13, -118.37),
        "Davenport": (47.65, -118.15),
        "Pullman": (46.73, -117.18),
    }.items():
        print(f"\n{name}: {get_soil(lat, lon)}")