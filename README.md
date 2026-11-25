# Cidade verde para quem?

**Calor, vegetação e renda nos setores censitários de Goiânia**

Goiânia é conhecida como uma das capitais mais arborizadas do Brasil. Este projeto investiga se o frescor e o verde estão distribuídos de forma parecida entre os setores censitários de maior e de menor renda. O produto final é um site narrativo e interativo, com mapas e gráficos, publicado pelo GitHub Pages a partir da pasta `docs/`.

Projeto final do bootcamp Future Tech Leaders / AEB (geoespacial). ODS relacionados: 3, 10, 11 e 13.

---

## 1. Objetivo

Responder à pergunta: **os setores censitários de menor renda de Goiânia têm menos vegetação, superfícies mais quentes e menos acesso a parques grandes?**

- **Unidade de análise:** setor censitário do Censo 2022 (IBGE), município 5208707.
- **Método:** cartografia e análise espacial descritiva, sem aprendizado de máquina. Os setores são divididos em cinco grupos de renda (quintis, Q1 a Q5), e a temperatura, a vegetação e a distância a parques são comparadas entre os grupos.
- **Natureza dos resultados:** associações, não causas.

**Principais resultados** (2.226 setores urbanos):

| Resultado | Valor |
|---|---|
| Diferença de temperatura do Q5 em relação à média dos grupos Q1 a Q4 | −1,15 °C |
| Correlação de Spearman entre renda e temperatura | −0,31 |
| Distância mediana até um parque grande (> 10 ha) | 0,9 km no Q5 e 3,1 km no Q1 |
| Setores prioritários: renda Q1/Q2, temperatura acima do percentil 75 e mais de 2 km de um parque grande | 225 (10,11%) |

## 2. Estrutura do projeto

```
goiania-thermal-justice/
├── data/
│   ├── raw/            Arquivos baixados do IBGE (não versionados; só o .gitkeep)
│   └── processed/      Tabelas geradas pelos notebooks (versionadas)
├── notebooks/          Análise, na ordem 01 → 06
├── scripts/            Etapas em Python chamadas a partir do notebook 06
├── outputs/
│   ├── figures/        Figuras estáticas (PNG)
│   ├── tables/         Tabelas de resultados (CSV)
│   └── web/            sectors.geojson: tabela final por setor, usada no site
├── cache/              Parques e bairros baixados do OpenStreetMap (gerado)
├── site/               Fonte do site (Quarto + Observable JS + MapLibre)
│   ├── index.qmd       Texto e cálculos da página
│   ├── styles.css      Estilo
│   ├── assets/         mapa.js, efeitos.js e imagens otimizadas
│   ├── data/           Cópias dos dados usados pelo site
│   └── figures/        Cópias das figuras estáticas
├── docs/               Site gerado (publicado pelo GitHub Pages)
├── pyproject.toml      Dependências (gerenciadas pelo uv)
└── uv.lock             Versões exatas das dependências
```

| Notebook ou script | O que faz | Principais saídas |
|---|---|---|
| `01_data_prep.ipynb` | Filtra a malha de Goiânia, junta a renda, cria os indicadores (`is_rural`, `small_sector`, `has_income`) e os quintis | `data/processed/sectors_income.gpkg` e `.csv` |
| `02_earth_engine.ipynb` | Primeira extração Landsat (temperatura de superfície nível 2 e NDVI) por setor, com diagnóstico de cobertura | `data/processed/sector_lst_ndvi.csv` |
| `03_analysis_and_maps.ipynb` | Primeira análise exploratória (substituída pelo notebook 06) | tabelas em `data/processed/` |
| `04_diagnostic.ipynb` | Diagnóstico de renda, NDVI e temperatura | (apenas leitura) |
| `05_urban_mask.ipynb` | Máscara urbana, NDVI e cobertura do solo (ESA WorldCover) por setor urbano | `data/processed/sector_stats_urban.csv` |
| `06_analysis_clean.ipynb` | Análise final: quintis, Spearman, cobertura do solo, regressões, extremos e figuras finais | `outputs/figures/`, `outputs/tables/` |
| `scripts/step3_4_prep.py` | Chamado pelo notebook 06: resíduos, vizinhança (Moran), distância a parques (OSM), rankings e a tabela do site | `outputs/web/sectors.geojson`, `cache/goiania_large_parks.gpkg` |
| `scripts/step_elev.py` | Altitude média por setor (SRTM, via Earth Engine) | `data/processed/sector_elevation.csv` |
| `scripts/step5_priority.py` | Marca os setores prioritários e gera a tabela de sensibilidade do critério | `outputs/web/sectors.geojson`, `outputs/tables/p6_prioridade_sensibilidade.csv` |

## 3. Como instalar as dependências

**Pré-requisitos**

- Linux, macOS ou Windows com **WSL2** (o projeto foi desenvolvido no WSL2 com Ubuntu).
- [uv](https://docs.astral.sh/uv/), para gerenciar o Python e os pacotes. Não use `pip` diretamente.
- Git.
- Para refazer o processamento de imagens: uma conta no **Google Earth Engine** associada a um projeto do Google Cloud.

**Instalação**

```bash
git clone https://github.com/HannahGrecco/goiania-thermal-justice.git
cd goiania-thermal-justice
uv sync
```

O `uv sync` cria o ambiente virtual `.venv` com o Python ≥ 3.13 e instala as dependências do `pyproject.toml`, incluindo o Quarto (grupo `dev`), usado para gerar o site.

**Earth Engine** (só para os notebooks 02 e 05 e o `step_elev.py`):

```bash
uv run earthengine authenticate
```

Depois troque o identificador do projeto do Google Cloud (`fourth-carport-512220-f2`) pelo seu, em `notebooks/02_earth_engine.ipynb`, `notebooks/05_urban_mask.ipynb` e `scripts/step_elev.py`.

## 4. Como executar o projeto

### Ver o site localmente (não precisa dos dados brutos)

O site já gerado está em `docs/`. Como a página carrega os dados com `fetch`, ela precisa de um servidor local; abrir o arquivo direto no navegador não funciona.

```bash
cd docs
uv run python -m http.server 8765
```

Depois abra <http://localhost:8765/>. O mapa precisa de internet para carregar o fundo da CARTO e as bibliotecas (jsDelivr).

### Gerar o site de novo

```bash
uv run quarto render site
```

A saída vai para `docs/`. O Quarto mostra dois avisos (`Refusing to remove directory ...` e `Quarto did not expect the path configuration ...`). Eles aparecem porque a pasta de saída fica fora de `site/` e não indicam erro.

### Rodar os notebooks

Abra a pasta no VS Code e use o kernel `.venv`, ou rode:

```bash
uv run jupyter lab
```

## 5. Como reproduzir os resultados

1. **Baixe os dados do IBGE (Censo 2022)** e salve em `data/raw/` com estes nomes:
   - `GO_setores_CD2022.gpkg`: malha de setores censitários de Goiás (malha definitiva).
   - `Agregados_por_setores_renda_responsavel_BR.csv`: agregados por setor, renda do responsável pelo domicílio (separador `;`).
2. **Rode os notebooks em ordem:** `01` → `02` → `05`. O `03` e o `04` são exploratórios e não são necessários para os resultados finais.
3. **Gere a temperatura de brilho por setor** em `data/processed/sector_stats_urban_v2.csv` (colunas `sector_id`, `lst_brightness_mean_c`, `lst_brightness_median_c`, `n_valid_bt_pixels`). Veja a seção 6: o código desta etapa ainda não está no repositório.
4. **Rode o notebook `06_analysis_clean.ipynb`.** Ele chama o `scripts/step3_4_prep.py`, que gera `outputs/web/sectors.geojson`.
5. **Rode os scripts complementares:**
   ```bash
   uv run python scripts/step_elev.py
   uv run python scripts/step5_priority.py
   ```
   Depois rode de novo as duas últimas células do notebook 06, que leem a tabela de sensibilidade.
6. **Atualize os dados do site e gere de novo:**
   ```bash
   cp outputs/web/sectors.geojson site/data/sectors.geojson
   uv run python -c "import geopandas as g; p=g.read_file('cache/goiania_large_parks.gpkg').to_crs(4326)[['name','geometry']].rename(columns={'name':'nome'}); p.to_file('site/data/parks.geojson', driver='GeoJSON')"
   cp outputs/figures/p6_*.png outputs/figures/p5_renda_distancia_lado_a_lado.png outputs/figures/p5_temp_por_faixa_parque.png site/figures/
   uv run quarto render site
   ```

**Conferência:** com o critério padrão, a seção "Onde agir primeiro" do site deve mostrar **225 setores**. Se o número for outro, a própria página mostra um aviso.

A ordem dos passos 4 e 5 foi reconstruída a partir das dependências entre os arquivos. Confira antes de uma reprodução completa.

## 6. Outras informações

### Convenções

- `CD_SETOR` / `sector_id` é sempre lido como texto (15 dígitos).
- Na tabela de renda do IBGE, `X` significa valor suprimido e vira ausente (`NaN`), não zero.
- Indicador de renda: **V06006**, rendimento mediano dos responsáveis com rendimento (julho de 2022).
- Sistemas de referência: a malha do IBGE está em SIRGAS 2000 (EPSG:4674). Áreas e distâncias são calculadas em SIRGAS 2000 / UTM 22S (EPSG:31982). O site usa EPSG:4326.
- Parque grande: polígono `leisure=park` do OpenStreetMap com mais de 10 hectares (19 parques).
- Temperatura: temperatura de brilho da banda térmica do Landsat 8/9, mediana de agosto e setembro de 2026, média por setor.

### Limites da análise

- Associação não é causa.
- A temperatura de brilho mede a superfície, não o ar nem a sensação térmica, e serve para comparar setores entre si.
- A renda é de 2022 e as imagens são de 2026.
- A renda considerada é só a do responsável pelo domicílio.
- Um valor por setor esconde diferenças internas, e setores muito pequenos têm valores menos confiáveis.

### Pendências conhecidas de reprodução

- O código que gera `data/processed/sector_stats_urban_v2.csv` (temperatura de brilho, nível 1) não está no repositório. Os notebooks 02 e 05 calculam apenas a temperatura de superfície do nível 2 (`ST_B10`).
- O teste de robustez "sem os setores que contêm um parque" e o modelo de regressão com altitude foram feitos fora dos notebooks atuais.

### Fontes de dados e créditos

- IBGE: Censo Demográfico 2022, malha de setores censitários e agregados de renda.
- USGS / NASA: Landsat 8 e 9, Collection 2, via Google Earth Engine.
- ESA WorldCover 2021 (10 m) e SRTM (30 m), via Google Earth Engine.
- OpenStreetMap: polígonos de parques (© colaboradores do OpenStreetMap).
- Mapa de fundo do site: CARTO Dark Matter.
- Fotos do site: Jackson Rodrigues / Prefeitura de Goiânia; reprodução / Curta Mais.

### Referências

- Foli, A. C. A. (2026). *Produção do espaço urbano, ilhas de calor e vulnerabilidade em Goiânia (GO): uma contribuição aos estudos da Geografia do Clima*. Tese de doutorado, UFG.
- Hsu, A., Sheriff, G., Chakraborty, T., & Manya, D. (2021). Disproportionate exposure to urban heat island intensity across major US cities. *Nature Communications*, 12, 2721. <https://doi.org/10.1038/s41467-021-22799-5>
- Sousa, S. B. de, & Ferreira, L. G. (2012). Análise da temperatura de superfície em ambientes urbanos: um estudo por meio de sensoriamento remoto no município de Goiânia, Goiás (2002–2011). *Confins*, 15. <https://doi.org/10.4000/confins.7631>
