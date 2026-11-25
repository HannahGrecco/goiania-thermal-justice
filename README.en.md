🇧🇷 Leia em português: [README.md](README.md)

# Cidade verde para quem? (A green city for whom?)

**Heat, vegetation and income across the census sectors of Goiânia, Brazil**

Goiânia is known as one of the most tree-covered state capitals in Brazil. This project investigates whether coolness and greenery are distributed in a similar way between higher-income and lower-income census sectors. The final product is an interactive, narrative website with maps and charts, published with GitHub Pages from the `docs/` folder. The website is in Brazilian Portuguese.

Capstone project of the Future Tech Leaders / AEB geospatial bootcamp. Related SDGs: 3, 10, 11 and 13.

---

## 1. Goal

**Problem.** Goiânia is one of the most tree-covered capitals in the country, but this average does not show how vegetation and heat are distributed across socioeconomic groups. The project investigates whether lower-income sectors have less vegetation and higher land surface temperatures.

**Goal.** Combine satellite data (NDVI and the thermal band of Landsat 8 and 9) with income from the 2022 Census, per census sector, to investigate:

- the unequal distribution of vegetation and heat across income groups;
- the association between vegetation and temperature;
- access to green areas, measured as the distance to the nearest large park.

The aim is to give decision-makers a basis for prioritizing tree planting and adaptation to heat waves, especially during the dry season of August and September.

**Product.** A spatial analysis published as an interactive web map with a guided narrative. The map has layers for temperature, income and distance to parks, plus a view of the sectors where low income, high heat and distance from green areas coincide. The final per-sector table and the code are public.

**Practical contribution.** Identifying the sectors where these conditions coincide lets public managers prioritize tree planting and heat adaptation where the risk is highest. The open, reproducible map also gives journalists and residents a basis for discussing these priorities.

**How the analysis was done**

- **Unit of analysis:** census sector of the 2022 Census (IBGE), municipality code 5208707.
- **Method:** descriptive cartography and spatial analysis, without machine learning, because the question is descriptive and the data are a table with one value per sector. Sectors are split into five income groups (quintiles, Q1 to Q5), and temperature, vegetation and distance to parks are compared across the groups.
- **Nature of the results:** associations, not causes.

**Main results** (2,226 urban sectors):

| Result | Value |
|---|---|
| Temperature difference of Q5 relative to the mean of groups Q1 to Q4 | −1.15 °C |
| Spearman correlation between income and temperature | −0.31 |
| Median distance to a large park (> 10 ha) | 0.9 km in Q5 and 3.1 km in Q1 |
| Priority sectors: income Q1/Q2, temperature above the 75th percentile and more than 2 km from a large park | 225 (10.11%) |

## 2. Project structure

```
goiania-thermal-justice/
├── data/
│   ├── raw/            Files downloaded from IBGE (not versioned; only .gitkeep)
│   └── processed/      Tables produced by the notebooks (versioned)
├── notebooks/          Analysis, in order 01 → 06
├── scripts/            Python steps called from notebook 06
├── outputs/
│   ├── figures/        Static figures (PNG)
│   ├── tables/         Result tables (CSV)
│   └── web/            sectors.geojson: final per-sector table, used by the website
├── cache/              OpenStreetMap extracts used in the analysis (parks, neighborhoods and context, 2026-11-15)
├── site/               Website source (Quarto + Observable JS + MapLibre)
│   ├── index.qmd       Page text and calculations
│   ├── styles.css      Styles
│   ├── assets/         mapa.js, efeitos.js and optimized images
│   ├── data/           Copies of the data used by the website
│   └── figures/        Copies of the static figures
├── docs/               Built website (published by GitHub Pages)
├── pyproject.toml      Dependencies (managed with uv)
└── uv.lock             Exact dependency versions
```

| Notebook or script | What it does | Main outputs |
|---|---|---|
| `01_data_prep.ipynb` | Filters the Goiânia sector mesh, joins income, creates the flags (`is_rural`, `small_sector`, `has_income`) and the quintiles | `data/processed/sectors_income.gpkg` and `.csv` |
| `02_earth_engine.ipynb` | First Landsat extraction per sector (Level 2 surface temperature and NDVI), with a coverage diagnostic | `data/processed/sector_lst_ndvi.csv` |
| `03_analysis_and_maps.ipynb` | First exploratory analysis (superseded by notebook 06) | tables in `data/processed/` |
| `04_diagnostic.ipynb` | Diagnostic of income, NDVI and temperature | (read only) |
| `05_urban_mask.ipynb` | Urban mask, NDVI and land cover (ESA WorldCover) per urban sector | `data/processed/sector_stats_urban.csv` |
| `06_analysis_clean.ipynb` | Final analysis: quintiles, Spearman, land cover, regressions, extremes and final figures | `outputs/figures/`, `outputs/tables/` |
| `scripts/step3_4_prep.py` | Called by notebook 06: residuals, spatial neighborhood (Moran), distance to parks (OSM), rankings and the website table | `outputs/web/sectors.geojson`, `cache/goiania_large_parks.gpkg` |
| `scripts/step_elev.py` | Mean elevation per sector (SRTM, via Earth Engine) | `data/processed/sector_elevation.csv` |
| `scripts/step5_priority.py` | Flags the priority sectors and builds the sensitivity table for the criterion | `outputs/web/sectors.geojson`, `outputs/tables/p6_prioridade_sensibilidade.csv` |

## 3. Installing the dependencies

**Requirements**

- Linux, macOS, or Windows with **WSL2** (the project was developed on WSL2 with Ubuntu).
- [uv](https://docs.astral.sh/uv/), to manage Python and the packages. Do not use `pip` directly.
- Git.
- To redo the image processing: a **Google Earth Engine** account linked to a Google Cloud project.

**Installation**

```bash
git clone https://github.com/HannahGrecco/goiania-thermal-justice.git
cd goiania-thermal-justice
uv sync
```

`uv sync` creates the `.venv` virtual environment with Python ≥ 3.13 and installs the dependencies from `pyproject.toml`, including Quarto (`dev` group), which builds the website.

**Earth Engine** (only for notebooks 02 and 05 and `step_elev.py`):

```bash
uv run earthengine authenticate
```

Then replace the Google Cloud project ID (`fourth-carport-512220-f2`) with your own in `notebooks/02_earth_engine.ipynb`, `notebooks/05_urban_mask.ipynb` and `scripts/step_elev.py`.

## 4. Running the project

### View the website locally (no raw data needed)

The built website is in `docs/`. Because the page loads its data with `fetch`, it needs a local server; opening the file directly in the browser does not work.

```bash
cd docs
uv run python -m http.server 8765
```

Then open <http://localhost:8765/>. The map needs an internet connection to load the CARTO basemap and the libraries (jsDelivr).

### Rebuild the website

```bash
uv run quarto render site
```

The output goes to `docs/`. Quarto prints two warnings (`Refusing to remove directory ...` and `Quarto did not expect the path configuration ...`). They appear because the output folder is outside `site/` and do not indicate an error.

### Run the notebooks

Open the folder in VS Code and use the `.venv` kernel, or run:

```bash
uv run jupyter lab
```

## 5. Reproducing the results

There are two paths. Path **A** redoes the final analysis from the processed tables that are already in the repository. It needs neither the raw IBGE data nor an Earth Engine account, and it was tested from scratch on a clean clone. Path **B** redoes everything from the raw data.

### A. Final analysis, from the processed data (recommended)

Requires only the installation from section 3 (`uv sync`) and an internet connection: the notebook downloads satellite basemap images for some figures.

1. **Run notebook 06 from start to finish.** Open `notebooks/06_analysis_clean.ipynb` in VS Code (`.venv` kernel) and run all cells, or run in the terminal:
   ```bash
   uv run jupyter nbconvert --to notebook --execute notebooks/06_analysis_clean.ipynb --output 06_executado.ipynb --ExecutePreprocessor.timeout=1800
   ```
   The notebook calls `scripts/step3_4_prep.py` and regenerates `outputs/figures/`, `outputs/tables/` and `outputs/web/sectors.geojson`. At the end it prints VIF ≈ 3.5, Moran's I ≈ 0.68 and 19 large parks. The script uses the OpenStreetMap extracts saved in `cache/`. If that folder is deleted, it downloads the data again, but the public OpenStreetMap server may refuse the request when it is busy, and new data may differ from the data used here.
2. **Build the sensitivity table for the priority criterion:**
   ```bash
   uv run python scripts/step5_priority.py
   ```
   It should print `N prioritários: 225` and `% dos elegíveis: 10.11%`. The script also adds a `priority` column to `outputs/web/sectors.geojson`; the other values do not change, and the website computes the priority on its own.
3. **Update the website data and rebuild the website:**
   ```bash
   cp outputs/web/sectors.geojson site/data/sectors.geojson
   uv run python -c "import geopandas as g; p=g.read_file('cache/goiania_large_parks.gpkg').to_crs(4326)[['name','geometry']].rename(columns={'name':'nome'}); p.to_file('site/data/parks.geojson', driver='GeoJSON')"
   cp outputs/figures/p6_*.png outputs/figures/p5_renda_distancia_lado_a_lado.png outputs/figures/p5_temp_por_faixa_parque.png site/figures/
   uv run quarto render site
   ```
4. **Check:** open the website (section 4). With the default criterion, the "Onde agir primeiro" (Where to act first) section should show **225 sectors**. If the number is different, the page itself shows a warning.

### B. From scratch, from the raw data

Requires, in addition to the installation, a Google Earth Engine account (section 3).

1. **Download the IBGE data (2022 Census)** and save it in `data/raw/` with these names:
   - `GO_setores_CD2022.gpkg`: census sector mesh for the state of Goiás (final mesh).
   - `Agregados_por_setores_renda_responsavel_BR.csv`: aggregates per sector, income of the household head (`;` separator).
2. **Run notebooks `01` → `02` → `05`.** They produce `sectors_income`, `sector_lst_ndvi.csv` and `sector_stats_urban.csv` in `data/processed/`. Notebooks `03` and `04` are exploratory and are not needed for the final results.
3. **Elevation per sector** (optional, Earth Engine): `uv run python scripts/step_elev.py`, which produces `data/processed/sector_elevation.csv`.
4. **Follow path A.**

The brightness temperature per sector (`data/processed/sector_stats_urban_v2.csv`), used by notebook 06, is in the repository, but the code that produced it is not. That is why path B uses this file as is.

## 6. Other information

### Conventions

- `CD_SETOR` / `sector_id` is always read as text (15 digits).
- In the IBGE income table, `X` means a suppressed value and becomes missing (`NaN`), not zero.
- Income indicator: **V06006**, median monthly income of household heads with income (July 2022).
- Coordinate reference systems: the IBGE mesh is in SIRGAS 2000 (EPSG:4674). Areas and distances are computed in SIRGAS 2000 / UTM 22S (EPSG:31982). The website uses EPSG:4326.
- Large park: OpenStreetMap `leisure=park` polygon larger than 10 hectares (19 parks).
- Temperature: brightness temperature from the Landsat 8/9 thermal band, median of August and September 2026, mean per sector.

### Limitations

- Association is not causation.
- Brightness temperature measures the surface, not the air or the perceived temperature, and is meant for comparing sectors with each other.
- Income is from 2022 and the images are from 2026.
- Income covers only the household head.
- One value per sector hides differences within it, and very small sectors have less reliable values.

### Data sources and credits

- IBGE: 2022 Demographic Census, census sector mesh and income aggregates.
- USGS / NASA: Landsat 8 and 9, Collection 2, via Google Earth Engine.
- ESA WorldCover 2021 (10 m) and SRTM (30 m), via Google Earth Engine.
- OpenStreetMap: park polygons (© OpenStreetMap contributors).
- Website basemap: CARTO Dark Matter.
- Website photos: Jackson Rodrigues / Prefeitura de Goiânia; reprodução / Curta Mais.

### References

- Foli, A. C. A. (2026). *Produção do espaço urbano, ilhas de calor e vulnerabilidade em Goiânia (GO): uma contribuição aos estudos da Geografia do Clima*. PhD thesis, Universidade Federal de Goiás (UFG).
- Hsu, A., Sheriff, G., Chakraborty, T., & Manya, D. (2021). Disproportionate exposure to urban heat island intensity across major US cities. *Nature Communications*, 12, 2721. <https://doi.org/10.1038/s41467-021-22799-5>
- Sousa, S. B. de, & Ferreira, L. G. (2012). Análise da temperatura de superfície em ambientes urbanos: um estudo por meio de sensoriamento remoto no município de Goiânia, Goiás (2002–2011). *Confins*, 15. <https://doi.org/10.4000/confins.7631>
