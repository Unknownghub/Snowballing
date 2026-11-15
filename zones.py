# Zone boundaries from Maaz et al. 2017 (Frontiers in Environmental Science 5:23):
# grain-fallow below 330 mm, transition up to 450 mm, annual cropping above.
LOW_MAX_MM = 330
HIGH_MIN_MM = 450

ZONE_LABELS = {
    "low": "Low rainfall (wheat-fallow)",
    "intermediate": "Intermediate rainfall (3-year rotation with fallow)",
    "high": "High rainfall (annual cropping)",
}


def zone_of(precip_mm):
    if precip_mm < LOW_MAX_MM:
        return "low"
    if precip_mm < HIGH_MIN_MM:
        return "intermediate"
    return "high"


def classify_zone(table):
    """Zone from the long-term average, plus how many single years agree."""
    mean_mm = table["precip_year_mm"].mean()
    zone = zone_of(mean_mm)
    zone_each_year = table["precip_year_mm"].apply(zone_of)
    return {
        "zone": zone,
        "label": ZONE_LABELS[zone],
        "mean_precip_mm": round(mean_mm),
        "share_of_years_in_zone": round((zone_each_year == zone).mean(), 2),
        "years_per_zone": zone_each_year.value_counts().to_dict(),
    }