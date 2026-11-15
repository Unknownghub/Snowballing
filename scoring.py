"""Step 6: replay each rotation over every past year and score it."""
import pandas as pd

from crops import (CROPS, WINTER_PEA_VS_WINTER_WHEAT, SW_AFTER_PEA_VS_AFTER_WHEAT,
                   TRITICALE_VS_WINTER_WHEAT, WW_LOSS_AFTER_PULSE_KG, WW_LOSS_AFTER_OILSEED_KG,
                   BARLEY_VS_SPRING_WHEAT, CANOLA_VS_SPRING_WHEAT)
from yield_model import KG_HA_PER_BU_AC, MAX_WHEAT_BU, wheat_yields
from rules import check_rotation, rotation_name

FORAGE_DRY_SPRING_LOSS = 0.20   # about 20% wheat loss after forage in a dry spring (Kahl et al. 2022)

# DESIGN CHOICES (not from the research): how notes and soil features turn into scores.
WARNING_PENALTY = 0.20
CAUTION_PENALTY = 0.05
SOIL_WEIGHTS = {"cover": 0.5, "residue": 0.25, "legume": 0.25}


def winter_wheat_bu(before, yields, dry_spring):
    """Winter wheat yield in each year, depending on the crop grown the year before."""
    after_fallow = yields["ww_after_fallow_bu"]
    group = CROPS[before]["group"]
    if group == "fallow":
        return after_fallow
    if group == "pulse":
        return (after_fallow - WW_LOSS_AFTER_PULSE_KG / KG_HA_PER_BU_AC).clip(lower=0)
    if group == "oilseed":
        return (after_fallow - WW_LOSS_AFTER_OILSEED_KG / KG_HA_PER_BU_AC).clip(lower=0)
    if group == "forage":
        return after_fallow.where(~dry_spring, after_fallow * (1 - FORAGE_DRY_SPRING_LOSS))
    return yields["ww_recrop_bu"]


def phase_yield_kg(rotation, i, yields, dry_spring):
    """Grain yield (kg/ha) of one rotation phase in each year, or None if not modelled."""
    crop, before = rotation[i], rotation[i - 1]
    if crop == "fallow":
        return yields["ww_recrop_bu"] * 0
    if crop == "winter_wheat":
        return winter_wheat_bu(before, yields, dry_spring) * KG_HA_PER_BU_AC
    if crop == "winter_triticale":
        return winter_wheat_bu(before, yields, dry_spring) * TRITICALE_VS_WINTER_WHEAT * KG_HA_PER_BU_AC
    if crop == "winter_pea":
        return winter_wheat_bu(before, yields, dry_spring) * WINTER_PEA_VS_WINTER_WHEAT * KG_HA_PER_BU_AC
    if crop == "spring_wheat":
        sw = yields["sw_recrop_bu"]
        if before == "winter_pea":
            sw = sw * SW_AFTER_PEA_VS_AFTER_WHEAT
        return sw * KG_HA_PER_BU_AC
    # Weak evidence: one farm, one year (Wilke farm 2023).
    if crop == "spring_barley":
        return yields["sw_recrop_bu"] * BARLEY_VS_SPRING_WHEAT * KG_HA_PER_BU_AC
    if crop == "canola":
        return yields["sw_recrop_bu"] * CANOLA_VS_SPRING_WHEAT * KG_HA_PER_BU_AC
    return None


def soil_score(rotation):
    n = len(rotation)
    covered = sum(c != "fallow" for c in rotation) / n
    good_residue = sum(CROPS[c]["residue"] == "high" for c in rotation) / n
    has_legume = float(any(CROPS[c]["legume"] for c in rotation))
    parts = {"cover": covered, "residue": good_residue, "legume": has_legume}
    score = sum(SOIL_WEIGHTS[k] * v for k, v in parts.items())
    return round(score, 2), {k: round(v, 2) for k, v in parts.items()}


def risk_score(notes):
    if any(n["level"] == "block" for n in notes):
        return 0.0
    warnings = sum(n["level"] == "warning" for n in notes)
    cautions = sum(n["level"] == "caution" for n in notes)
    return round(max(0.0, 1 - WARNING_PENALTY * warnings - CAUTION_PENALTY * cautions), 2)


def evaluate(rotation, table, site):
    """Everything the tool knows about one rotation at one site."""
    yields = wheat_yields(table)
    spring = table[["precip_apr_mm", "precip_may_mm", "precip_jun_mm"]].sum(axis=1)
    dry_spring = spring < spring.median()   # DESIGN CHOICE: "dry spring" = below this site's median

    phases, missing, weak = [], [], []
    for i, crop in enumerate(rotation):
        result = phase_yield_kg(rotation, i, yields, dry_spring)
        if result is None:
            missing.append(CROPS[crop]["name"])
            result = yields["ww_recrop_bu"] * 0   # no yield source: counted as zero grain
        if crop in ("spring_barley", "canola"):
            weak.append(CROPS[crop]["name"])
        phases.append(result)

    # Each year, every phase is grown on part of the farm: average them.
    yearly_grain = pd.concat(phases, axis=1).mean(axis=1).dropna()
    capped = (yields["ww_after_fallow_bu"] >= MAX_WHEAT_BU).mean() > 0.5 and "winter_wheat" in rotation

    notes = check_rotation(rotation, site)
    soil, soil_parts = soil_score(rotation)
    return {
        "rotation": rotation,
        "name": rotation_name(rotation),
        "grain_p10": round(yearly_grain.quantile(0.10)),
        "grain_p50": round(yearly_grain.quantile(0.50)),
        "grain_p90": round(yearly_grain.quantile(0.90)),
        "years": len(yearly_grain),
        "not_modelled": missing,
        "weak_yield_evidence": weak,
        "capped_yields": bool(capped),
        "soil": soil,
        "soil_parts": soil_parts,
        "risk": risk_score(notes),
        "blocked": any(n["level"] == "block" for n in notes),
        "notes": notes,
    }


def rank(results, weights):
    """weights: {"yield", "dry_years", "soil", "risk"} from the farmer's sliders."""
    best_typical = max(r["grain_p50"] for r in results) or 1
    best_dry = max(r["grain_p10"] for r in results) or 1
    total_weight = sum(weights.values()) or 1
    for r in results:
        parts = {
            "yield": r["grain_p50"] / best_typical,
            "dry_years": r["grain_p10"] / best_dry,
            "soil": r["soil"],
            "risk": r["risk"],
        }
        r["scores"] = {k: round(v, 2) for k, v in parts.items()}
        r["total"] = 0.0 if r["blocked"] else round(
            sum(weights[k] * parts[k] for k in parts) / total_weight, 2)
    return sorted(results, key=lambda r: r["total"], reverse=True)


if __name__ == "__main__":
    from climate import crop_year_table
    from zones import classify_zone
    from rules import CANDIDATES

    sites = {"Ritzville": (47.13, -118.37), "Davenport": (47.65, -118.15), "Pullman": (46.73, -117.18)}
    weights = {"yield": 1, "dry_years": 1, "soil": 1, "risk": 1}
    for name, (lat, lon) in sites.items():
        table = crop_year_table(lat, lon)
        zone = classify_zone(table)
        site = {"zone": zone["zone"], "mean_precip_mm": zone["mean_precip_mm"],
                "soil_ph": None, "slope_pct": None}
        results = [evaluate(rot, table, site) for rot in CANDIDATES[site["zone"]]]
        print(f"\n===== {name}: {zone['label']} =====")
        for r in rank(results, weights):
            print(f"\n  {r['total']:.2f}  {r['name']}")
            print(f"        grain kg/ha/yr: dry year {r['grain_p10']}, typical {r['grain_p50']}, good year {r['grain_p90']}"
                  f"  ({r['years']} years)")
            print(f"        scores {r['scores']}  soil parts {r['soil_parts']}")
            if r["not_modelled"]:
                print(f"        no yield source, counted as zero: {', '.join(r['not_modelled'])}")
            if r["weak_yield_evidence"]:
                print(f"        yield from one farm, one year: {', '.join(r['weak_yield_evidence'])}")
            if r["capped_yields"]:
                print("        winter wheat after fallow hits the yield cap in most years")