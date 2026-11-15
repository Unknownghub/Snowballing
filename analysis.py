"""Everything the web page needs for one field, in one call."""
from climate import crop_year_table
from rules import CANDIDATES
from scoring import evaluate, rank
from soil import get_soil
from yield_model import within_calibration
from zones import classify_zone

# Why each candidate rotation is offered: (one line, source).
REASONS = {
    ("winter_wheat", "fallow"):
        ("Regional standard at low rainfall. Fallow stores water for wheat.", "WSU EM049E"),
    ("winter_wheat", "spring_wheat", "fallow"):
        ("Adds a crop. Fallow every third year kept wheat yields in regional studies.",
         "Maaz et al. 2017"),
    ("winter_pea", "spring_wheat", "fallow"):
        ("Ritzville trial: half the grain, no nitrogen fertilizer, more spring wheat after.",
         "Schillinger 2017"),
    ("winter_wheat", "spring_wheat", "forage_cover"):
        ("Forage replaces fallow: ground stays covered, with hay or grazing.",
         "Kahl, Boone and Brooks 2022"),
    ("winter_wheat", "canola", "winter_wheat", "fallow"):
        ("WSU Davenport farm rotation. Higher returns than its 3-year rotation, 2018-23.",
         "Esser and Appel 2024"),
    ("winter_wheat", "spring_wheat", "spring_pea"):
        ("Typical annual cropping at high rainfall, with a pulse.", "WSU EM049E"),
    ("winter_wheat", "canola", "winter_pea"):
        ("Based on the long-term USDA no-till experiment at Pullman.", "Huggins et al. 2024"),
    ("winter_wheat", "spring_barley", "lentil"):
        ("Long-standing crops of the annual-cropping area.", "WSU EM049E"),
}


def analyse(lat, lon, current_rotation, soil_ph, weights):
    table = crop_year_table(lat, lon)
    zone = classify_zone(table)
    calibrated, mean_inches = within_calibration(table)

    try:
        soil = get_soil(lat, lon)
        soil_error = None
    except Exception as error:   # the soil service can be slow or down
        soil, soil_error = None, str(error)

    site = {
        "zone": zone["zone"],
        "mean_precip_mm": zone["mean_precip_mm"],
        "soil_ph": soil_ph,                       # from the farmer's soil test only
        "slope_pct": soil["slope_pct"] if soil else None,
    }

    rotations = [current_rotation] + [r for r in CANDIDATES[zone["zone"]] if r != current_rotation]
    results = []
    for rotation in rotations:
        result = evaluate(rotation, table, site)
        result["is_current"] = rotation == current_rotation
        reason, source = REASONS.get(tuple(rotation), ("The rotation you entered.", None))
        result["reason"] = reason
        result["reason_source"] = source
        results.append(result)

    return {
        "zone": zone,
        "calibrated": calibrated,
        "mean_inches": mean_inches,
        "frost_free_days": table["frost_free_days"].median(),
        "hot_days": table["hot_days_may_jul"].median(),
        "years": len(table),
        "first_year": int(table.index.min()),
        "last_year": int(table.index.max()),
        "soil": soil,
        "soil_error": soil_error,
        "results": rank(results, weights),
    }
