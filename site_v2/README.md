# site_v2: storytelling interativo (versão 2)

Versão interativa de "Cidade verde para quem?". É uma página única em Quarto com
Observable JS (OJS), Observable Plot e MapLibre GL JS. A renderização não executa Python.

## Relação com a v1

- A v1 (estática) fica em `site/` e é publicada em `docs/` (`docs/index.html`). Ela é o plano B
  e não é tocada por nada desta pasta.
- A v2 fica em `site_v2/` e é publicada em `docs/v2/`. No GitHub Pages ela abre em `<site>/v2/`.
- O texto vem de `site/index.qmd`. As figuras estáticas foram trocadas por gráficos e mapas
  interativos, e as originais (cópias em `figures/`) ficam num bloco recolhível no fim da página.

## Estrutura

| Caminho | O que é |
|---|---|
| `_quarto.yml` | configuração (saída em `../docs/v2`, bibliotecas por CDN com versão fixa) |
| `index.qmd` | texto e células OJS (cálculos, gráficos, controles) |
| `styles.css` | estilo editorial escuro |
| `assets/mapa.js` | módulo do mapa (camadas, legenda, tooltip, popup, simulação) |
| `data/sectors.geojson` | cópia sem alteração de `outputs/web/sectors.geojson` |
| `data/parks.geojson` | `cache/goiania_large_parks.gpkg` convertido para EPSG:4326 |
| `figures/` | cópias das figuras de `site/figures/` |

Todos os números do texto são calculados no navegador a partir de `data/sectors.geojson`.
Isso inclui a contagem de setores, a diferença Q5 − Q1–Q4, as distâncias por quintil, os
prioritários e o Spearman. Os únicos números escritos à mão vêm do texto da v1 (regressão, VIF,
Moran, 513 setores do nível 2). A marcação de prioridade é calculada na página assim:
quintil 1 ou 2, temperatura acima do percentil 75 de todos os setores e distância ao parque
maior que 2.000 m. O resultado esperado é 225 setores, e a página mostra um aviso se der outro número.

## Atualizar os dados

Rode na raiz do repositório. A cópia não altera os originais.

```bash
cp outputs/web/sectors.geojson site_v2/data/sectors.geojson
uv run python -c "import geopandas as g; p=g.read_file('cache/goiania_large_parks.gpkg').to_crs(4326)[['name','geometry']].rename(columns={'name':'nome'}); p.to_file('site_v2/data/parks.geojson', driver='GeoJSON')"
```

## Renderizar

```bash
uv run quarto render site_v2
```

O Quarto mostra dois avisos (`Refusing to remove directory .../docs/v2/site_libs`). Eles
aparecem porque a pasta de saída fica fora de `site_v2/` e são esperados. Não renderize `site/`
a partir daqui.

## Visualizar localmente

O OJS carrega os dados com `fetch`, então a página precisa de um servidor. Abrir o arquivo
direto não funciona.

```bash
cd docs && uv run python -m http.server 8765
```

Abra <http://localhost:8765/v2/>. A v1 continua em <http://localhost:8765/>.

O mapa precisa de internet para o basemap da CARTO e para as bibliotecas (jsDelivr). Sem o
basemap, o mapa usa um fundo liso e continua funcionando.
