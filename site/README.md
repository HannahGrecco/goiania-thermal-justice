# site: storytelling interativo

Fonte do site "Cidade verde para quem?". É uma página única em Quarto, com Observable JS (OJS), Observable Plot e MapLibre GL JS. A renderização não executa Python: todos os números da página são calculados no navegador a partir de `data/sectors.geojson`.

A saída vai para `../docs/`, que é a pasta publicada pelo GitHub Pages.

## Estrutura

| Caminho | O que é |
|---|---|
| `_quarto.yml` | Configuração: saída em `../docs`, fontes e bibliotecas por CDN com versão fixa |
| `index.qmd` | Texto e células OJS (cálculos, gráficos e controles) |
| `styles.css` | Estilo editorial escuro (Source Serif 4 e Source Sans 3) |
| `assets/mapa.js` | Módulo do mapa: camadas, legenda, tooltip, popup e simulação |
| `assets/efeitos.js` | Fade-in ao rolar, parallax leve e índice escondido sobre a capa. Desligados com `prefers-reduced-motion`; o parallax também é desligado no celular |
| `assets/img/` | Imagens otimizadas: recortes das figuras do projeto (capa e faixas) e fotos das manchetes |
| `data/sectors.geojson` | Cópia sem alteração de `outputs/web/sectors.geojson` |
| `data/parks.geojson` | `cache/goiania_large_parks.gpkg` convertido para EPSG:4326 |
| `figures/` | Cópias das figuras de `outputs/figures/` usadas no bloco "Figuras estáticas" |

A marcação de setor prioritário é calculada na página: quintil 1 ou 2, temperatura acima do percentil 75 de todos os setores e distância a parque grande maior que 2.000 m. O resultado esperado é 225 setores, e a página mostra um aviso se der outro número.

## Atualizar os dados

Rode na raiz do repositório. As cópias não alteram os originais.

```bash
cp outputs/web/sectors.geojson site/data/sectors.geojson
uv run python -c "import geopandas as g; p=g.read_file('cache/goiania_large_parks.gpkg').to_crs(4326)[['name','geometry']].rename(columns={'name':'nome'}); p.to_file('site/data/parks.geojson', driver='GeoJSON')"
```

## Renderizar e visualizar

```bash
uv run quarto render site
cd docs && uv run python -m http.server 8765
```

Abra <http://localhost:8765/>. O Quarto mostra dois avisos sobre a pasta de saída ficar fora de `site/`; eles são esperados. O mapa precisa de internet para o fundo da CARTO e para as bibliotecas (jsDelivr). Sem o fundo, o mapa usa uma cor lisa e continua funcionando.
