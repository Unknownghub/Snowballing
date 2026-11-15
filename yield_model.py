import pandas as pd

MM_PER_INCH = 25.4
KG_HA_PER_BU_AC = 67.25

# Assumptions (see LIMITATIONS.md):
OVERWINTER_EFF = 0.62  # share of Sep-Mar precipitation stored; Schillinger 2017 measured 55-69%
FALLOW_EFF = 0.30      # share of fallow-year precipitation stored; Maaz et al. 2017
MAX_WHEAT_BU = 101     # cap: yields peaked near 6,800 kg/ha (Maaz et al. 2017)
CALIBRATED_IN = (9.5, 13.8)  # yearly precipitation at the EM049E study sites, inches


def wheat_yields(table):
    """Modelled wheat yield (bushels/acre) for every crop year, from WSU EM049E."""
    inches = table / MM_PER_INCH
    overwinter = inches["precip_sep_mar_mm"] * OVERWINTER_EFF
    fallow_water = inches["precip_year_mm"].shift(1) * FALLOW_EFF
    apr = inches["precip_apr_mm"]
    may = inches["precip_may_mm"]
    jun = inches["precip_jun_mm"]

    ww_after_fallow = (6.7 * fallow_water + 7.9 * overwinter
                       + 4.4 * apr + 7.6 * may + 12.2 * jun - 16.4)
    sw_recrop = 5.4 * overwinter + 1.4 * apr + 6.4 * may + 5.7 * jun - 10.6
    ww_recrop = 5.7 * overwinter + 6.6 * (apr + may + jun) - 14.7

    yields = pd.DataFrame({
        "ww_after_fallow_bu": ww_after_fallow,
        "ww_recrop_bu": ww_recrop,
        "sw_recrop_bu": sw_recrop,
    })
    return yields.clip(lower=0, upper=MAX_WHEAT_BU).round(1)


def within_calibration(table):
    mean_in = table["precip_year_mm"].mean() / MM_PER_INCH
    low, high = CALIBRATED_IN
    return low <= mean_in <= high, round(mean_in, 1)


if __name__ == "__main__":
    from climate import crop_year_table
    from zones import classify_zone

    sites = {
        "Ritzville": (47.13, -118.37),
        "Davenport": (47.65, -118.15),
        "Pullman": (46.73, -117.18),
    }
    for name, (lat, lon) in sites.items():
        table = crop_year_table(lat, lon)
        zone = classify_zone(table)
        ok, mean_in = within_calibration(table)
        yields = wheat_yields(table)
        print(f"\n=== {name} ===")
        print(f"Zone: {zone['label']}  ({zone['mean_precip_mm']} mm a year)")
        print(f"Years falling in that zone: {zone['share_of_years_in_zone']:.0%}  {zone['years_per_zone']}")
        print(f"Inside the equations' calibration range: {ok}  ({mean_in} in a year)")
        summary = yields.describe(percentiles=[0.1, 0.5, 0.9]).loc[["10%", "50%", "90%"]]
        print(summary.round(1))
    davenport = crop_year_table(47.65, -118.15)
    print("\nDavenport 2023 precipitation (mm):", davenport.loc[2023, "precip_year_mm"])
    print(wheat_yields(davenport).loc[2023])