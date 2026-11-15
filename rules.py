
from crops import CROPS

KEEP_FALLOW_BELOW_MM = 350   # Maaz et al. 2017: wheat after crops yields less below 350 mm
STEEP_SLOPE_PCT = 10         # DESIGN CHOICE: no published threshold found

CANDIDATES = {
    "low": [
        ["winter_wheat", "fallow"],
        ["winter_wheat", "spring_wheat", "fallow"],
        ["winter_pea", "spring_wheat", "fallow"],
    ],
    "intermediate": [
        ["winter_wheat", "spring_wheat", "fallow"],
        ["winter_wheat", "spring_wheat", "forage_cover"],
        ["winter_wheat", "canola", "winter_wheat", "fallow"],
    ],
    "high": [
        ["winter_wheat", "spring_wheat", "spring_pea"],
        ["winter_wheat", "canola", "winter_pea"],
        ["winter_wheat", "spring_barley", "lentil"],
    ],
}


def rotation_name(rotation):
    return " → ".join(CROPS[c]["name"] for c in rotation)


def note(level, rule, message, source):
    return {"level": level, "rule": rule, "message": message, "source": source}


def years_between(rotation, position, species):
    """Years until the same species comes back, treating the rotation as a repeating cycle."""
    n = len(rotation)
    for step in range(1, n + 1):
        crop = rotation[(position + step) % n]
        if CROPS[crop]["species"] == species:
            return step
    return None


def check_rotation(rotation, site):
    """site: {"zone", "mean_precip_mm", "soil_ph" (or None), "slope_pct" (or None)}"""
    notes = []
    n = len(rotation)
    zone = site["zone"]
    ph = site.get("soil_ph")
    slope = site.get("slope_pct")

    for i, crop in enumerate(rotation):
        info = CROPS[crop]
        before = rotation[i - 1]  # previous year, wrapping around the cycle

        # Rule 1: keep fallow before winter wheat in dry places.
        if crop == "winter_wheat" and before != "fallow" \
                and site["mean_precip_mm"] < KEEP_FALLOW_BELOW_MM:
            notes.append(note("warning", 1,
                f"Winter wheat after {CROPS[before]['name'].lower()} instead of fallow: "
                f"below {KEEP_FALLOW_BELOW_MM} mm a year, wheat yields less after a crop than after fallow.",
                "Maaz et al. 2017"))

        # Rule 7: soil acidity.
        if info["critical_ph"] is not None and ph is not None:
            low, high = info["critical_ph"]
            limit = f"{low}" if low == high else f"{low}-{high}"
            if ph < low:
                level = "block" if info["legume"] else "warning"
                notes.append(note(level, 7,
                    f"{info['name']}: soil pH {ph} is below its critical value ({limit}); "
                    "yields drop sharply below it. Risk is highest on soils that were once forest.",
                    "Koenig et al., WSU FS050E"))
            elif ph < high:
                notes.append(note("caution", 7,
                    f"{info['name']}: soil pH {ph} is inside its critical range ({limit}). "
                    "Monitor pH; liming may be needed.",
                    "Koenig et al., WSU FS050E"))
        if info["legume"] and ph is None:
            notes.append(note("warning", 7,
                f"{info['name']}: soil pH unknown. Legumes are the most acid-sensitive crops here; "
                "measured pH below 5.0 occurs across the Palouse. Get a soil test first.",
                "WSU soil acidification; Koenig et al. FS050E"))

        # Return intervals for break crops.
        if info["return_years"] is not None:
            gap = years_between(rotation, i, info["species"])
            if gap is not None and gap < info["return_years"]:
                notes.append(note("caution", "interval",
                    f"{info['name']} returns every {gap} years; European guidance suggests at least "
                    f"{info['return_years']} to limit soil-borne disease. Check local experience.",
                    "Académie d'agriculture de France; LfULG Saxony"))

        # Rule 4: wind erosion when a low-residue crop is followed by fallow in the dry zone.
        after = rotation[(i + 1) % n]
        if zone == "low" and info["residue"] == "low" and after == "fallow":
            notes.append(note("warning", 4,
                f"{info['name']} leaves little residue before fallow: higher wind-erosion risk. "
                "No-till or undercutter fallow cut soil loss 15-65% in trials.",
                "Schillinger 2017; Sharratt and Feng 2009"))

        # Rule 8: canola.
        if crop == "canola":
            notes.append(note("caution", 8,
                "Canola breaks cereal disease and grass-weed cycles, but local long-term trials found "
                "lower wheat yields after canola, linked to less soil water stored over winter.",
                "WSU Oilseeds; Schillinger, Paulitz and Hansen 2023"))

        # Rule 5: forage cover crop timing.
        if crop == "forage_cover":
            notes.append(note("info", 5,
                "Forage in place of fallow: no wheat yield loss in a wet spring, about 20% loss in a dry "
                "spring. Ending it 2-4 weeks earlier removes most of the loss.",
                "Kahl, Boone and Brooks 2022"))

    # Rule 9: cereal root disease in the high zone.
    cereals = sum(CROPS[c]["group"] == "cereal" for c in rotation)
    if zone == "high" and cereals / n > 2 / 3:
        notes.append(note("caution", 9,
            "More than two years in three are cereals: higher risk of cereal-only root diseases "
            "(take-all, eyespot, Cephalosporium stripe).",
            "Smiley, Paulitz and Marshall 2012, PNW 639"))

    # Rule 10: water erosion on slopes.
    bare_or_low = any(c == "fallow" or CROPS[c]["residue"] == "low" for c in rotation)
    if zone == "high" and bare_or_low:
        if slope is None:
            notes.append(note("info", 10,
                "Slope unknown. On steep Palouse slopes, bare or low-residue years raise water-erosion risk.",
                "USGS Fact Sheet 069-98"))
        elif slope >= STEEP_SLOPE_PCT:
            notes.append(note("warning", 10,
                f"Slope about {slope}%: bare or low-residue years raise water-erosion risk. "
                "No-till seeding cut predicted erosion by about 9 tons/acre/year.",
                "USGS Fact Sheet 069-98"))

    # Rule 11: soil carbon direction.
    if "fallow" in rotation:
        notes.append(note("info", 11,
            "Includes fallow: long-term trials show soil carbon declining under wheat-fallow.",
            "USDA-ARS Pendleton long-term experiments"))

    # Remove exact duplicates (a crop appearing twice gives the same note twice).
    unique = []
    for item in notes:
        if item not in unique:
            unique.append(item)
    return unique


if __name__ == "__main__":
    sites = {
        "Ritzville": {"zone": "low", "mean_precip_mm": 310, "soil_ph": None, "slope_pct": None},
        "Davenport": {"zone": "intermediate", "mean_precip_mm": 340, "soil_ph": 5.4, "slope_pct": None},
        "Pullman": {"zone": "high", "mean_precip_mm": 506, "soil_ph": 5.3, "slope_pct": 15},
    }
    for name, site in sites.items():
        print(f"\n===== {name} ({site['zone']} zone, pH {site['soil_ph']}) =====")
        for rotation in CANDIDATES[site["zone"]]:
            print(f"\n  {rotation_name(rotation)}")
            for n in check_rotation(rotation, site):
                print(f"    [{n['level'].upper()}] {n['message']}  ({n['source']})")