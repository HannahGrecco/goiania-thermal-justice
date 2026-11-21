from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
WEB = ROOT / "outputs" / "web"
TABLES = ROOT / "outputs" / "tables"

SECTOR_GEOJSON = WEB / "sectors.geojson"
INCOME_CSV = PROCESSED / "sectors_income.csv"
TEMPERATURE_CSV = PROCESSED / "sector_stats_urban_v2.csv"


def main() -> None:
    sectors = gpd.read_file(SECTOR_GEOJSON)
    sectors["sector_id"] = sectors["sector_id"].astype("string")

    income = pd.read_csv(
        INCOME_CSV,
        usecols=["sector_id", "small_sector", "is_rural", "area_km2", "income_quintile"],
    )
    income["sector_id"] = income["sector_id"].astype("string")

    temperature = pd.read_csv(
        TEMPERATURE_CSV,
        usecols=["sector_id", "lst_brightness_mean_c"],
    )
    temperature["sector_id"] = temperature["sector_id"].astype("string")

    sectors = sectors.merge(
        income,
        on="sector_id",
        how="left",
        validate="one_to_one",
    ).merge(
        temperature,
        on="sector_id",
        how="left",
        validate="one_to_one",
    )

    if "quintil" in sectors.columns:
        sectors["priority_quintile"] = sectors["quintil"]
    else:
        sectors["priority_quintile"] = sectors["income_quintile"]

    eligible = (
        sectors["is_rural"].eq(False)
        & sectors["small_sector"].eq(False)
        & sectors["lst_brightness_mean_c"].notna()
    )
    eligible_sectors = sectors.loc[eligible].copy()

    temperature_threshold = eligible_sectors["lst_brightness_mean_c"].quantile(0.75)
    sectors["priority"] = (
        eligible
        & sectors["priority_quintile"].isin([1, 2])
        & sectors["lst_brightness_mean_c"].gt(temperature_threshold)
        & sectors["dist_park_m"].gt(2000)
    ).astype("int8")

    sectors = sectors.drop(
        columns=[
            "small_sector",
            "is_rural",
            "area_km2",
            "income_quintile",
            "lst_brightness_mean_c",
            "priority_quintile",
        ],
        errors="ignore",
    )

    sectors.to_file(SECTOR_GEOJSON, driver="GeoJSON")

    sensitivity_rows = []
    for distance_m in [1500, 2000, 3000]:
        for percentile in [70, 75, 80]:
            temperature_cutoff = eligible_sectors["lst_brightness_mean_c"].quantile(
                percentile / 100
            )
            priority = (
                eligible_sectors["priority_quintile"].isin([1, 2])
                & eligible_sectors["lst_brightness_mean_c"].gt(temperature_cutoff)
                & eligible_sectors["dist_park_m"].gt(distance_m)
            )
            n_priority = int(priority.sum())
            sensitivity_rows.append(
                {
                    "distance_m": distance_m,
                    "temperature_percentile": percentile,
                    "n_priority": n_priority,
                    "pct_priority": round(
                        100 * n_priority / len(eligible_sectors),
                        6,
                    ),
                }
            )

    sensitivity = pd.DataFrame(sensitivity_rows)
    TABLES.mkdir(parents=True, exist_ok=True)
    sensitivity_path = TABLES / "p6_prioridade_sensibilidade.csv"
    sensitivity.to_csv(sensitivity_path, index=False)

    sectors_with_priority = gpd.read_file(SECTOR_GEOJSON)
    sectors_with_priority["sector_id"] = sectors_with_priority["sector_id"].astype("string")
    sectors_with_priority = sectors_with_priority.merge(
        income[
            ["sector_id", "small_sector", "is_rural", "area_km2"]
        ],
        on="sector_id",
        how="left",
        validate="one_to_one",
    ).merge(
        temperature,
        on="sector_id",
        how="left",
        validate="one_to_one",
    )

    priority_mask = sectors_with_priority["priority"].eq(1)
    eligible_mask = (
        sectors_with_priority["is_rural"].eq(False)
        & sectors_with_priority["small_sector"].eq(False)
        & sectors_with_priority["lst_brightness_mean_c"].notna()
    )
    eligible_comparison = sectors_with_priority.loc[eligible_mask].copy()
    priority_comparison = eligible_comparison.loc[priority_mask.loc[eligible_mask]]
    remaining_comparison = eligible_comparison.loc[~priority_mask.loc[eligible_mask]]

    n_priority = int(priority_mask.sum())
    pct_priority = 100 * n_priority / len(eligible_comparison)
    print(f"N prioritários: {n_priority}")
    print(f"% dos elegíveis: {pct_priority:.2f}%")

    priority_area = priority_comparison["area_km2"].median()
    remaining_area = remaining_comparison["area_km2"].median()
    print(
        f"Área mediana: prioritários {priority_area:.6f} km²; "
        f"demais elegíveis {remaining_area:.6f} km²"
    )

    priority_income = priority_comparison["income_median"].median()
    remaining_income = remaining_comparison["income_median"].median()
    print(
        f"Renda mediana: prioritários R$ {priority_income:.2f}; "
        f"demais elegíveis R$ {remaining_income:.2f}"
    )

    priority_temperature = priority_comparison["lst_brightness_mean_c"].mean()
    remaining_temperature = remaining_comparison["lst_brightness_mean_c"].mean()
    print(
        f"Temperatura média: prioritários {priority_temperature:.2f} °C; "
        f"demais elegíveis {remaining_temperature:.2f} °C"
    )


if __name__ == "__main__":
    main()
