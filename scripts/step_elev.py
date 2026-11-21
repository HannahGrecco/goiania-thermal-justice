from pathlib import Path

import ee
import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "outputs" / "web" / "sectors.geojson"
OUTPUT = ROOT / "data" / "processed" / "sector_elevation.csv"
EE_PROJECT = "fourth-carport-512220-f2"

ee.Initialize(project=EE_PROJECT)

sectors = gpd.read_file(INPUT).to_crs("EPSG:4326")
features = [
    ee.Feature(
        ee.Geometry(row.geometry.__geo_interface__),
        {"sector_id": str(row.sector_id)},
    )
    for row in sectors.itertuples()
]
sector_collection = ee.FeatureCollection(features)
elevation = ee.Image("USGS/SRTMGL1_003").select("elevation")
reduced = elevation.reduceRegions(
    collection=sector_collection,
    reducer=ee.Reducer.mean(),
    scale=30,
    tileScale=4,
)

rows = reduced.getInfo()["features"]
result = [
    {
        "sector_id": feature["properties"]["sector_id"],
        "elev_mean_m": feature["properties"].get("mean"),
    }
    for feature in rows
]
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(result).to_csv(OUTPUT, index=False)
print(f"Saved {len(result)} sectors to {OUTPUT}")
