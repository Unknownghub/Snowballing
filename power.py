import os
import requests
import pandas as pd

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FILL_VALUE = -999.0
CACHE_DIR = "cache"

# NASA POWER precipitation was 28-41% above published long-term averages
# Regional correction; see limitations.txt
PRECIP_SCALE = 0.75

NAMES = {
    "T2M_MAX": "tmax_c",
    "T2M_MIN": "tmin_c",
    "PRECTOTCORR": "precip_mm",
}


def get_daily_weather(lat, lon, start="19810101", end="20260831"):
    """Daily NASA POWER weather for one point, as a table."""
    cache_file = os.path.join(
        CACHE_DIR, f"power_{lat:.2f}_{lon:.2f}_{start}_{end}.csv"
    )
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, parse_dates=["date"])
        df["precip_adj_mm"] = df["precip_mm"] * PRECIP_SCALE
        return df

    params = {
        "parameters": ",".join(NAMES.keys()),
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": start,
        "end": end,
        "format": "JSON",
    }
    response = requests.get(URL, params=params, timeout=300)
    response.raise_for_status()
    values = response.json()["properties"]["parameter"]

    df = pd.DataFrame(values)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.rename(columns=NAMES)
    df = df.replace(FILL_VALUE, float("nan"))
    df = df.reset_index()

    os.makedirs(CACHE_DIR, exist_ok=True)
    df.to_csv(cache_file, index=False)

    df["precip_adj_mm"] = df["precip_mm"] * PRECIP_SCALE
    return df


if __name__ == "__main__":
    df = get_daily_weather(46.73, -117.18)
    yearly = df.groupby(df["date"].dt.year)[["precip_mm", "precip_adj_mm"]].sum()
    print("NASA original (mm):", round(yearly.loc[1982:2025, "precip_mm"].mean()))
    print("Corrected (mm):    ", round(yearly.loc[1982:2025, "precip_adj_mm"].mean()))