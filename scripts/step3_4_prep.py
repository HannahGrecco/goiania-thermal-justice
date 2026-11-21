from pathlib import Path
import time

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
import statsmodels.api as sm
from esda.moran import Moran
from libpysal.weights import Queen
from statsmodels.stats.outliers_influence import variance_inflation_factor


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
CACHE = ROOT / "cache"
WEB = ROOT / "outputs" / "web"
TABLES.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)
WEB.mkdir(parents=True, exist_ok=True)

analysis = pd.read_csv(TABLES / "analysis_df.csv")
analysis_raw_sector_ids = analysis["sector_id"].copy()
analysis["sector_id"] = analysis["sector_id"].astype("string").str.zfill(15)
context_columns = [
    "pct_built",
    "pct_tree",
    "pct_grass",
    "pct_bare",
    "pct_cropland",
    "pct_water",
]
missing_context_columns = [
    column for column in context_columns if column not in analysis.columns
]
if missing_context_columns:
    context_stats = pd.read_csv(
        ROOT / "data" / "processed" / "sector_stats_urban.csv",
        usecols=["sector_id", *missing_context_columns],
    )
    context_stats["sector_id"] = context_stats["sector_id"].astype("string").str.zfill(15)
    analysis = analysis.merge(
        context_stats,
        on="sector_id",
        how="left",
        validate="one_to_one",
    )
sectors = gpd.read_file(ROOT / "data" / "processed" / "sectors_income.gpkg")[
    ["sector_id", "geometry"]
]
sectors["sector_id"] = sectors["sector_id"].astype("string").str.zfill(15)
sectors = sectors.merge(analysis, on="sector_id", how="inner", validate="one_to_one")

predictors = sectors[["ndvi_mean", "pct_built"]]
model = sm.OLS(
    sectors["lst_brightness_mean_c"],
    sm.add_constant(predictors),
).fit()
sectors["resid"] = model.resid

vif_data = sm.add_constant(predictors)
vif = {
    column: variance_inflation_factor(vif_data.values, index)
    for index, column in enumerate(vif_data.columns)
    if column != "const"
}
weights = Queen.from_dataframe(sectors, use_index=False)
weights.transform = "r"
moran = Moran(sectors["resid"], weights)

parks_cache = CACHE / "goiania_large_parks.gpkg"
if parks_cache.exists():
    parks = gpd.read_file(parks_cache)
else:
    parks = ox.features_from_place(
        "Goiânia, Goiás, Brazil",
        tags={"leisure": "park"},
    ).reset_index(drop=True)
    parks = parks[parks.geometry.notna()]
    parks = parks[parks.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    parks = parks.to_crs("EPSG:31982")
    parks = parks.loc[parks.geometry.area > 10 * 10_000].copy()
    parks.to_file(parks_cache, driver="GPKG")
parks = parks.to_crs("EPSG:31982")
parks = parks[parks.geometry.area > 10 * 10_000].copy()
park_count = len(parks)

sectors_utm = sectors.to_crs("EPSG:31982")
centroids = sectors_utm[["sector_id", "geometry"]].copy()
centroids["geometry"] = centroids.geometry.centroid
nearest = gpd.sjoin_nearest(
    centroids,
    parks[["geometry"]],
    how="left",
    distance_col="dist_park_m",
)
distances = nearest.groupby("sector_id", as_index=False)["dist_park_m"].min()
sectors = sectors.merge(distances, on="sector_id", how="left", validate="one_to_one")

parks_boundary = sectors.to_crs("EPSG:4326").geometry.unary_union
osm_cache = CACHE / "bairros_osm.gpkg"
osm_queries = {
    "boundary=administrative, admin_level=10": {
        "boundary": "administrative",
        "admin_level": "10",
    },
    "place=suburb": {"place": "suburb"},
    "place=neighbourhood": {"place": "neighbourhood"},
}
if osm_cache.exists():
    neighborhoods = gpd.read_file(osm_cache)
    for source_tag, group in neighborhoods.groupby("source_tag"):
        print(
            f"OSM {source_tag}: polígonos={len(group)}; "
            f"com_nome={group['name'].notna().sum()}"
        )
else:
    osm_frames = []
    for source_tag, tags in osm_queries.items():
        features = ox.features_from_polygon(parks_boundary, tags=tags).reset_index(drop=True)
        total = len(features)
        features = features.loc[
            features.geometry.notna()
            & features.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        ].copy()
        features["name"] = features["name"].astype("string").str.strip()
        features.loc[features["name"].isin(["", "nan", "<NA>"]), "name"] = pd.NA
        named = features.loc[features["name"].notna(), ["name", "geometry"]].copy()
        named["source_tag"] = source_tag
        osm_frames.append(named)
        print(f"OSM {source_tag}: polígonos={total}; com_nome={len(named)}")
    neighborhoods = gpd.GeoDataFrame(
        pd.concat(osm_frames, ignore_index=True),
        geometry="geometry",
        crs="EPSG:4326",
    ).to_crs("EPSG:31982")
    neighborhoods["_geometry_key"] = neighborhoods.geometry.apply(lambda value: value.wkb_hex)
    neighborhoods = neighborhoods.drop_duplicates("_geometry_key").drop(
        columns="_geometry_key"
    )
    neighborhoods["area_m2"] = neighborhoods.geometry.area
    neighborhoods.to_file(osm_cache, driver="GPKG")

neighborhoods = neighborhoods.to_crs("EPSG:31982")
neighborhoods["area_m2"] = neighborhoods.geometry.area
discard_mask = (neighborhoods["area_m2"] > 15 * 1_000_000) | neighborhoods[
    "name"
].eq("Goiânia")
discarded_neighborhoods = neighborhoods.loc[discard_mask]
if not discarded_neighborhoods.empty:
    print("Polígonos descartados antes do sjoin:")
    print(
        discarded_neighborhoods.assign(
            area_km2=discarded_neighborhoods["area_m2"] / 1_000_000
        )[["name", "area_km2"]].to_string(index=False)
    )
neighborhoods = neighborhoods.loc[~discard_mask].copy()
centroids = sectors.to_crs("EPSG:31982")[["sector_id", "geometry"]].copy()
centroids["geometry"] = centroids.geometry.centroid
centroid_matches = gpd.sjoin(
    centroids,
    neighborhoods[["name", "source_tag", "area_m2", "geometry"]],
    how="inner",
    predicate="within",
)
centroid_matches = (
    centroid_matches.sort_values(["sector_id", "area_m2"])
    .drop_duplicates("sector_id")
    .rename(columns={"name": "bairro"})
)
sector_bairros = centroid_matches[["sector_id", "bairro", "source_tag"]]
sectors = sectors.merge(
    sector_bairros,
    on="sector_id",
    how="left",
    validate="one_to_one",
)

valid_bairro = sectors["bairro"].notna()
unmatched_centroids = centroids.loc[
    ~centroids["sector_id"].isin(centroid_matches["sector_id"])
]
if unmatched_centroids.empty:
    nearest_ref = pd.DataFrame(columns=["sector_id", "name", "dist_bairro_m"])
else:
    nearest_ref = gpd.sjoin_nearest(
        unmatched_centroids,
        neighborhoods[["name", "geometry"]],
        how="left",
        distance_col="dist_bairro_m",
    )
nearest_ref = (
    nearest_ref.sort_values(["sector_id", "dist_bairro_m"])
    .drop_duplicates("sector_id")
)
sectors["nome_ref"] = sectors["bairro"].fillna("sem bairro mapeado")
sectors["tipo_ref"] = sectors["bairro"].notna().map(
    {True: "dentro", False: "sem bairro mapeado"}
)
nearby = nearest_ref.loc[nearest_ref["dist_bairro_m"] < 300]
if not nearby.empty:
    nearby_ids = nearby.set_index("sector_id")
    nearby_mask = sectors["sector_id"].isin(nearby_ids.index)
    sectors.loc[nearby_mask, "nome_ref"] = sectors.loc[
        nearby_mask, "sector_id"
    ].map(nearby_ids["name"])
    sectors.loc[nearby_mask, "tipo_ref"] = "próximo a"

rank_weights = Queen.from_dataframe(sectors, use_index=False)
temp_suav = np.empty(len(sectors))
resid_suav = np.empty(len(sectors))
for index, neighbors in rank_weights.neighbors.items():
    indexes = [index, *neighbors]
    weights = sectors.iloc[indexes]["n_valid_bt_pixels"].to_numpy()
    temp_suav[index] = np.average(
        sectors.iloc[indexes]["lst_brightness_mean_c"], weights=weights
    )
    resid_suav[index] = np.average(sectors.iloc[indexes]["resid"], weights=weights)
sectors["temp_suav"] = temp_suav
sectors["resid_suav"] = resid_suav

pixel_threshold = sectors["n_valid_bt_pixels"].quantile(0.25)
eligibility_diagnostic = sectors.assign(
    excl_small=sectors["small_sector"],
    excl_rural=sectors["is_rural"],
    excl_pixels=sectors["n_valid_bt_pixels"] <= pixel_threshold,
).groupby("income_quintile", observed=False).agg(
    n_setores=("sector_id", "size"),
    excl_small=("excl_small", "sum"),
    excl_rural=("excl_rural", "sum"),
    excl_pixels=("excl_pixels", "sum"),
)
print("Diagnóstico de elegibilidade:")
print(eligibility_diagnostic.to_string())

eligible = ~sectors["small_sector"] & ~sectors["is_rural"]
eligibility_by_quintile = (
    sectors.assign(elegivel=eligible)
    .groupby("income_quintile", observed=False)["elegivel"]
    .agg(n_setores="size", n_elegiveis="sum")
)
eligibility_by_quintile["pct_elegivel"] = (
    eligibility_by_quintile["n_elegiveis"]
    / eligibility_by_quintile["n_setores"]
    * 100
)
print("Percentual elegível por quintil:")
print(eligibility_by_quintile.to_string())

rank_columns = [
    "sector_id",
    "nome_ref",
    "tipo_ref",
    "income_median",
    "income_quintile",
    "lst_brightness_mean_c",
    "temp_suav",
    "resid",
    "resid_suav",
    "pct_built",
    "pct_tree",
    "pct_water",
    "ndvi_mean",
    "dist_park_m",
    "n_valid_bt_pixels",
]
small_by_quintile = (
    sectors.groupby("income_quintile", observed=False)["small_sector"]
    .agg(n_setores="size", n_small="sum")
)
hot_indices = set(sectors.loc[eligible].nlargest(10, "temp_suav").index)
cold_indices = set(sectors.loc[eligible].nsmallest(10, "temp_suav").index)
extreme_indices = hot_indices | cold_indices
small_extreme = int(sectors.loc[list(extreme_indices), "small_sector"].sum())
print("small_sector por quintil:")
print(small_by_quintile.to_string())
print(f"small_sector entre os 20 extremos: {small_extreme}")
if small_extreme:
    print("AVISO: há setores small_sector entre os 20 extremos.")
rank_output = sectors.loc[eligible, rank_columns].rename(
    columns={
        "income_quintile": "quintil",
        "lst_brightness_mean_c": "temp",
    }
)
ranking_columns = [
    "sector_id",
    "nome_ref",
    "tipo_ref",
    "income_median",
    "pct_tree",
    "pct_water",
    "pct_built",
    "dist_park_m",
]
for label, selected in [
    ("10 mais quentes por temp_suav", rank_output.nlargest(10, "temp_suav")),
    ("10 mais frios por temp_suav", rank_output.nsmallest(10, "temp_suav")),
    ("10 maiores resíduos suavizados", rank_output.nlargest(10, "resid_suav")),
    ("10 menores resíduos suavizados", rank_output.nsmallest(10, "resid_suav")),
]:
    print(label + ":")
    score = "temp_suav" if "temperatura" in label or "quentes" in label or "frios" in label else "resid_suav"
    print(selected[ranking_columns + [score]].to_string(index=False))

extreme_neighbors = {
    index: set(rank_weights.neighbors[index]) & extreme_indices
    for index in extreme_indices
}
components = []
remaining = set(extreme_indices)
while remaining:
    component = {remaining.pop()}
    changed = True
    while changed:
        changed = False
        connected = {
            index
            for index in remaining
            if any(index in extreme_neighbors[other] for other in component)
            or any(other in extreme_neighbors[index] for other in component)
        }
        if connected:
            component.update(connected)
            remaining.difference_update(connected)
            changed = True
    components.append(sorted(component))

sectors_utm = sectors.to_crs("EPSG:31982")
patch_rows = []
for component in components:
    component_data = sectors.iloc[component]
    component_geometry = sectors_utm.iloc[component].geometry.union_all()
    component_centroid = (
        gpd.GeoSeries([component_geometry], crs="EPSG:31982")
        .centroid.to_crs("EPSG:4326")
        .iloc[0]
    )
    patch_rows.append(
        {
            "n_setores": len(component),
            "latitude": component_centroid.y,
            "longitude": component_centroid.x,
            "renda_mediana": component_data["income_median"].median(),
            "pct_tree_medio": component_data["pct_tree"].mean(),
            "pct_water_medio": component_data["pct_water"].mean(),
            "temp_suav_media": component_data["temp_suav"].mean(),
            "tipo": "quente" if any(index in hot_indices for index in component) else "fria",
        }
    )
patches = pd.DataFrame(patch_rows).sort_values(["tipo", "temp_suav_media"])
print("Manchas extremas:")
print(patches.to_string(index=False))
patches.to_csv(TABLES / "p4_manchas.csv", index=False)

context_boundary = sectors.to_crs("EPSG:4326").geometry.union_all()
ox.settings.requests_timeout = 45
context_queries = {
    "aeroway": {"aeroway": ["aerodrome", "runway"]},
    "landuse": {"landuse": ["industrial", "commercial", "retail"]},
    "water": [
        {"natural": "water"},
        {"waterway": ["river", "riverbank"]},
    ],
}
context_features = {}
for context_name, tags in context_queries.items():
    context_cache = CACHE / f"context_{context_name}.gpkg"
    if context_cache.exists():
        features = gpd.read_file(context_cache)
    else:
        features = None
        last_error = None
        query_tags = tags if isinstance(tags, list) else [tags]
        for endpoint in [
            "https://overpass.kumi.systems/api",
            "https://overpass.private.coffee/api",
            "https://overpass-api.de/api",
        ]:
            ox.settings.overpass_url = endpoint
            for attempt in range(2):
                try:
                    downloaded = [
                        ox.features_from_polygon(context_boundary, tags=part_tags)
                        for part_tags in query_tags
                    ]
                    features = pd.concat(downloaded, ignore_index=True)
                    features = features.loc[
                        ~features.index.duplicated()
                    ].reset_index(drop=True)
                    break
                except Exception as error:
                    last_error = error
                    time.sleep(2**attempt)
            if features is not None:
                break
        if features is None:
            raise RuntimeError(
                f"Não foi possível baixar as feições OSM de {context_name}."
            ) from last_error
        features = features.loc[features.geometry.notna()].copy().to_crs("EPSG:31982")
        features.to_file(context_cache, driver="GPKG")
    context_features[context_name] = features.to_crs("EPSG:31982")


def nearest_distance(point, features):
    if features.empty:
        return np.nan
    return point.distance(features.geometry.union_all())


landuse = context_features["landuse"]
industrial = landuse.loc[
    landuse["landuse"].eq("industrial")
] if "landuse" in landuse else landuse.iloc[0:0]
commercial = landuse.loc[
    landuse["landuse"].isin(["commercial", "retail"])
] if "landuse" in landuse else landuse.iloc[0:0]
context_rows = []
for mancha_id, component in enumerate(components, start=1):
    component_data = sectors.iloc[component]
    component_geometry = sectors_utm.iloc[component].geometry.union_all()
    component_centroid = (
        gpd.GeoSeries([component_geometry], crs="EPSG:31982")
        .centroid.to_crs("EPSG:4326")
        .iloc[0]
    )
    pct_values = component_data[
        ["pct_built", "pct_tree", "pct_grass", "pct_bare", "pct_cropland", "pct_water"]
    ].mean()
    distances = {
        "dist_aeroway_m": nearest_distance(
            gpd.GeoSeries([component_geometry], crs="EPSG:31982").centroid.iloc[0],
            context_features["aeroway"],
        ),
        "dist_industrial_m": nearest_distance(
            gpd.GeoSeries([component_geometry], crs="EPSG:31982").centroid.iloc[0],
            industrial,
        ),
        "dist_commercial_m": nearest_distance(
            gpd.GeoSeries([component_geometry], crs="EPSG:31982").centroid.iloc[0],
            commercial,
        ),
        "dist_park_m": nearest_distance(
            gpd.GeoSeries([component_geometry], crs="EPSG:31982").centroid.iloc[0],
            parks,
        ),
        "dist_water_m": nearest_distance(
            gpd.GeoSeries([component_geometry], crs="EPSG:31982").centroid.iloc[0],
            context_features["water"],
        ),
    }
    tips = []
    if distances["dist_aeroway_m"] < 500:
        tips.append("aeroporto")
    if min(distances["dist_industrial_m"], distances["dist_commercial_m"]) < 200:
        tips.append("industrial/comercial")
    if distances["dist_park_m"] < 300:
        tips.append("parque")
    if distances["dist_water_m"] < 300 or pct_values["pct_water"] > 5:
        tips.append("água")
    if pct_values["pct_bare"] > 15:
        tips.append("solo exposto/obra")
    if not tips:
        tips.append("residencial")
    context_rows.append(
        {
            "mancha_id": mancha_id,
            "sector_ids": ",".join(component_data["sector_id"].tolist()),
            "latitude": component_centroid.y,
            "longitude": component_centroid.x,
            "tipo": "quente" if any(index in hot_indices for index in component) else "fria",
            "temp_suav": component_data["temp_suav"].mean(),
            "renda_mediana": component_data["income_median"].median(),
            **distances,
            **pct_values.to_dict(),
            "dica_automatica": "; ".join(tips),
        }
    )
context_table = pd.DataFrame(context_rows)
print("Contexto das manchas:")
print(context_table.to_string(index=False))
context_table.to_csv(TABLES / "p4_manchas_contexto.csv", index=False)
rank_output.to_csv(TABLES / "p4_setores_rank.csv", index=False)

sectors.drop(columns="geometry").to_csv(TABLES / "p3_sectors.csv", index=False)
web_columns = {
    "income_quintile": "quintil",
    "lst_brightness_mean_c": "temperatura",
}
web_sectors = sectors[
    [
        "sector_id",
        "income_median",
        "income_quintile",
        "lst_brightness_mean_c",
        "resid",
        "dist_park_m",
        "pct_built",
        "pct_tree",
        "ndvi_mean",
        "geometry",
    ]
].rename(columns=web_columns)
web_sectors = web_sectors.to_crs("EPSG:4326")
web_sectors.to_file(WEB / "sectors.geojson", driver="GeoJSON")

print(f"VIF: ndvi_mean={vif['ndvi_mean']:.6f}; pct_built={vif['pct_built']:.6f}")
print(f"Moran's I dos resíduos: {moran.I:.6f}")
print(f"Parques grandes encontrados: {park_count}")
