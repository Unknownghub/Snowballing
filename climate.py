import pandas as pd
from power import get_daily_weather

FROST_C = 0.0   # a frost day: minimum air temperature at or below 0 C
HOT_C = 30.0    # DESIGN CHOICE, not from the research: shown for information only

WINTER_MONTHS = [9, 10, 11, 12, 1, 2, 3]


def frost_free_days(daily):
    """Days between the last spring frost and the first autumn frost, per calendar year."""
    result = {}
    for year, days in daily.groupby(daily["date"].dt.year):
        frosts = days[days["tmin_c"] <= FROST_C]
        spring = frosts[frosts["date"].dt.month <= 7]
        autumn = frosts[frosts["date"].dt.month >= 8]
        if spring.empty or autumn.empty:
            continue
        gap = autumn["date"].min() - spring["date"].max()
        result[year] = gap.days - 1
    return pd.Series(result, name="frost_free_days")


def crop_year_table(lat, lon):
    """One row per crop year (September to August), named by its harvest year."""
    daily = get_daily_weather(lat, lon)
    month = daily["date"].dt.month
    rain = daily["precip_adj_mm"]

    daily["crop_year"] = daily["date"].dt.year + (month >= 9).astype(int)
    daily["rain_sep_mar"] = rain.where(month.isin(WINTER_MONTHS), 0)
    daily["rain_apr"] = rain.where(month == 4, 0)
    daily["rain_may"] = rain.where(month == 5, 0)
    daily["rain_jun"] = rain.where(month == 6, 0)
    daily["hot_day"] = (daily["tmax_c"] >= HOT_C) & month.isin([5, 6, 7])

    table = daily.groupby("crop_year").agg(
        days=("date", "count"),
        precip_year_mm=("precip_adj_mm", "sum"),
        precip_sep_mar_mm=("rain_sep_mar", "sum"),
        precip_apr_mm=("rain_apr", "sum"),
        precip_may_mm=("rain_may", "sum"),
        precip_jun_mm=("rain_jun", "sum"),
        hot_days_may_jul=("hot_day", "sum"),
    )
    table = table[table["days"] >= 365].drop(columns="days")
    table["frost_free_days"] = frost_free_days(daily).reindex(table.index)
    return table.round(1)


if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    table = crop_year_table(47.13, -118.37)
    print(table.head())
    print(table.tail(3))
    print(len(table), "crop years")
    share_winter = table["precip_sep_mar_mm"].sum() / table["precip_year_mm"].sum()
    spring = table[["precip_apr_mm", "precip_may_mm", "precip_jun_mm"]].sum(axis=1)
    share_spring = spring.sum() / table["precip_year_mm"].sum()
    print("Share of yearly precipitation, Sep-Mar:", round(share_winter * 100), "%")
    print("Share of yearly precipitation, Apr-Jun:", round(share_spring * 100), "%")