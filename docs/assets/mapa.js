// Mapa interativo dos setores censitários (MapLibre GL JS).
// A biblioteca é carregada no cabeçalho da página (ver _quarto.yml) e fica em window.maplibregl.
// Este módulo é importado pelas células OJS do index.qmd.

const ESTILO_BASE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
// Estilo reserva: fundo liso, usado se o basemap da CARTO não carregar (ex.: sem internet).
const ESTILO_RESERVA = {
  version: 8,
  sources: {},
  layers: [{ id: "fundo", type: "background", paint: { "background-color": "#0e0e0e" } }],
};

const DESTAQUE = "#fdae61";
const NEUTRO = "#4a4a4a";
const CLARO = "#f0ece4";
const COR_PARQUE = "#9ecae1";

export const CORES_TEMPERATURA = ["#2c7bb6", "#abd9e9", "#ffffbf", "#fdae61", "#d7191c"];
export const CORES_QUINTIL = ["#3b528b", "#21918c", "#5ec962", "#b5de2b", "#fde725"];
// Faixas de cor da distância (em metros). São só cortes de cor, não resultados.
export const PARADAS_DISTANCIA = [0, 500, 1000, 2000, 4000, 8000];
export const CORES_DISTANCIA = ["#e5f5e0", "#a1d99b", "#74c476", "#31a354", "#1b5e3a", "#0d2b1c"];

const fmt = (x, casas = 2) =>
  Number(x).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const fmtRenda = (x) => "R$ " + Number(x).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const fmtKm = (m) => (m / 1000).toLocaleString("pt-BR");

const NOMES = {
  temperatura: "Temperatura de superfície",
  quintil: "Quintil de renda",
  distancia: "Distância ao parque grande",
  prioridade: "Setores prioritários",
  simulacao: "Simulação",
};

async function carregarEstilo() {
  // Baixa o estilo da CARTO com tempo-limite; se falhar, usa o fundo liso.
  try {
    const controle = new AbortController();
    const tempo = setTimeout(() => controle.abort(), 8000);
    const resposta = await fetch(ESTILO_BASE, { signal: controle.signal });
    clearTimeout(tempo);
    if (!resposta.ok) throw new Error(resposta.status);
    return await resposta.json();
  } catch (erro) {
    console.warn("Basemap CARTO indisponível, usando fundo liso.", erro);
    return ESTILO_RESERVA;
  }
}

function limites(geojson) {
  // Caixa envolvente [[oeste, sul], [leste, norte]] de todas as coordenadas.
  let o = Infinity, s = Infinity, l = -Infinity, n = -Infinity;
  const visitar = (c) => {
    if (typeof c[0] === "number") {
      o = Math.min(o, c[0]); l = Math.max(l, c[0]);
      s = Math.min(s, c[1]); n = Math.max(n, c[1]);
    } else c.forEach(visitar);
  };
  geojson.features.forEach((f) => f.geometry && visitar(f.geometry.coordinates));
  return [[o, s], [l, n]];
}

function corPreenchimento(camada, paradasTemp) {
  switch (camada) {
    case "temperatura":
      return ["interpolate", ["linear"], ["get", "temperatura"],
        ...paradasTemp.flatMap((p, i) => [p, CORES_TEMPERATURA[i]])];
    case "quintil":
      return ["match", ["get", "quintil"],
        1, CORES_QUINTIL[0], 2, CORES_QUINTIL[1], 3, CORES_QUINTIL[2],
        4, CORES_QUINTIL[3], 5, CORES_QUINTIL[4], NEUTRO];
    case "distancia":
      return ["interpolate", ["linear"], ["get", "dist_park_m"],
        ...PARADAS_DISTANCIA.flatMap((p, i) => [p, CORES_DISTANCIA[i]])];
    case "prioridade":
      return ["case", ["boolean", ["feature-state", "prio"], false], DESTAQUE, NEUTRO];
    case "simulacao":
      return ["case", ["boolean", ["feature-state", "sim"], false], DESTAQUE, NEUTRO];
  }
}

function opacidade(camada) {
  if (camada === "prioridade") return ["case", ["boolean", ["feature-state", "prio"], false], 0.92, 0.4];
  if (camada === "simulacao") return ["case", ["boolean", ["feature-state", "sim"], false], 0.92, 0.4];
  return 0.85;
}

function valorTooltip(camada, p, estado) {
  switch (camada) {
    case "temperatura": return `${fmt(p.temperatura)} °C`;
    case "quintil": return `Q${p.quintil} · renda mediana ${fmtRenda(p.income_median)}`;
    case "distancia": return `${fmt(p.dist_park_m / 1000)} km do parque grande mais próximo`;
    case "prioridade": return estado.prio ? "prioritário" : "não prioritário";
    case "simulacao": return estado.sim ? "entra na simulação" : "fora da simulação";
  }
}

function htmlPopup(p, estado) {
  const linhas = [
    ["Setor", p.sector_id],
    ["Renda mediana", fmtRenda(p.income_median)],
    ["Quintil de renda", `Q${p.quintil}`],
    ["Temperatura", `${fmt(p.temperatura)} °C`],
    ["Distância ao parque", `${fmt(p.dist_park_m / 1000)} km`],
    ["Prioritário (critério do estudo)", estado.prio ? "sim" : "não"],
  ];
  return `<table class="popup-tabela">${linhas
    .map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`)
    .join("")}</table>`;
}

function htmlLegenda(camada, opcoes, extra) {
  const gradiente = (cores) => `linear-gradient(to right, ${cores.join(", ")})`;
  const parque = `<div class="leg-item"><span class="leg-linha" style="border-color:${COR_PARQUE}"></span>Parque grande (> 10 ha)</div>`;
  let corpo = "";
  if (camada === "temperatura") {
    const p = opcoes.paradasTemp;
    corpo = `<div class="leg-barra" style="background:${gradiente(CORES_TEMPERATURA)}"></div>
      <div class="leg-rotulos">${p.map((v) => `<span>${fmt(v, 1)}</span>`).join("")}</div>
      <div class="leg-nota">°C · cores nos percentis 5, 25, 50, 75 e 95 dos setores</div>`;
  } else if (camada === "quintil") {
    corpo = opcoes.faixasRenda
      .map((f, i) => `<div class="leg-item"><span class="leg-caixa" style="background:${CORES_QUINTIL[i]}"></span>
        Q${f.quintil} · ${fmtRenda(f.min)}–${fmtRenda(f.max)}</div>`)
      .join("") + `<div class="leg-nota">renda mediana do responsável (Censo 2022)</div>`;
  } else if (camada === "distancia") {
    corpo = `<div class="leg-barra" style="background:${gradiente(CORES_DISTANCIA)}"></div>
      <div class="leg-rotulos">${PARADAS_DISTANCIA.map((v) => `<span>${fmtKm(v)}</span>`).join("")}</div>
      <div class="leg-nota">km do centro do setor ao parque grande mais próximo</div>${parque}`;
  } else if (camada === "prioridade") {
    corpo = `<div class="leg-item"><span class="leg-caixa" style="background:${DESTAQUE}"></span>Prioritário (${extra?.nPrio ?? "?"} setores)</div>
      <div class="leg-item"><span class="leg-caixa" style="background:${NEUTRO}"></span>Demais setores</div>${parque}`;
  } else if (camada === "simulacao") {
    corpo = `<div class="leg-item"><span class="leg-caixa" style="background:${DESTAQUE}"></span>Entra na simulação</div>
      <div class="leg-item"><span class="leg-linha tracejada" style="border-color:${CLARO}"></span>Estava no critério do estudo e saiu</div>
      <div class="leg-item"><span class="leg-caixa" style="background:${NEUTRO}"></span>Demais setores</div>${parque}`;
  }
  return `<div class="leg-titulo">${NOMES[camada]}</div>${corpo}`;
}

/**
 * Cria um mapa dentro de `el`.
 * opcoes: { setores, parques, camada, paradasTemp, faixasRenda, idsPrioritarios }
 * Devolve um controlador com: pronto, mostrarCamada, definirConjunto, destacarQuintil, atualizarLegenda.
 */
export function criarMapa(el, opcoes) {
  const maplibregl = window.maplibregl;
  if (!maplibregl) throw new Error("MapLibre GL JS não carregou.");

  el.classList.add("mapa-container");
  const tooltip = document.createElement("div");
  tooltip.className = "mapa-tooltip";
  const legenda = document.createElement("div");
  legenda.className = "mapa-legenda";
  el.append(tooltip, legenda);

  let camada = opcoes.camada ?? "temperatura";
  let extraLegenda = { nPrio: opcoes.idsPrioritarios?.size };
  const estados = new Map(); // id -> {prio, sim}
  opcoes.setores.features.forEach((f) =>
    estados.set(f.properties.sector_id, { prio: opcoes.idsPrioritarios?.has(f.properties.sector_id) ?? false, sim: false }));

  let mapa;
  const pronto = carregarEstilo().then(
    (estilo) =>
      new Promise((resolver) => {
        mapa = new maplibregl.Map({
          container: el,
          style: estilo,
          bounds: limites(opcoes.setores),
          fitBoundsOptions: { padding: 24 },
          attributionControl: { compact: true },
          cooperativeGestures: true,
          locale: {
            "CooperativeGesturesHandler.WindowsHelpText": "Use Ctrl + rolagem para dar zoom no mapa",
            "CooperativeGesturesHandler.MacHelpText": "Use ⌘ + rolagem para dar zoom no mapa",
            "CooperativeGesturesHandler.MobileHelpText": "Use dois dedos para mover o mapa",
          },
        });
        mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
        mapa.on("load", () => {
          // as camadas dos setores entram abaixo dos rótulos do basemap
          const primeiroRotulo = mapa.getStyle().layers.find((c) => c.type === "symbol")?.id;
          mapa.addSource("setores", { type: "geojson", data: opcoes.setores, promoteId: "sector_id" });
          mapa.addSource("parques", { type: "geojson", data: opcoes.parques });
          mapa.addLayer({ id: "setores-fill", type: "fill", source: "setores",
            paint: { "fill-color": corPreenchimento(camada, opcoes.paradasTemp), "fill-opacity": opacidade(camada) } }, primeiroRotulo);
          mapa.addLayer({ id: "setores-borda", type: "line", source: "setores",
            paint: { "line-color": "#0e0e0e", "line-width": 0.25, "line-opacity": 0.6 } }, primeiroRotulo);
          mapa.addLayer({ id: "setores-saiu", type: "line", source: "setores",
            layout: { visibility: "none" },
            paint: { "line-color": CLARO, "line-width": 1.3, "line-dasharray": [2, 1.5],
              "line-opacity": ["case", ["all", ["boolean", ["feature-state", "prio"], false],
                ["!", ["boolean", ["feature-state", "sim"], false]]], 1, 0] } }, primeiroRotulo);
          mapa.addLayer({ id: "setores-destaque", type: "line", source: "setores",
            filter: ["==", ["get", "quintil"], -1],
            paint: { "line-color": CLARO, "line-width": 1.1 } }, primeiroRotulo);
          mapa.addLayer({ id: "parques-contorno", type: "line", source: "parques",
            layout: { visibility: "none" },
            paint: { "line-color": COR_PARQUE, "line-width": 1.6 } }, primeiroRotulo);
          mapa.addLayer({ id: "setores-hover", type: "line", source: "setores",
            paint: { "line-color": CLARO,
              "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 2.2, 0] } }, primeiroRotulo);

          estados.forEach((e, id) => mapa.setFeatureState({ source: "setores", id }, e));
          ligarEventos();
          aplicarCamada();
          resolver();
        });
      })
  );

  function aplicarCamada() {
    mapa.setPaintProperty("setores-fill", "fill-color", corPreenchimento(camada, opcoes.paradasTemp));
    mapa.setPaintProperty("setores-fill", "fill-opacity", opacidade(camada));
    const comParques = ["distancia", "prioridade", "simulacao"].includes(camada);
    mapa.setLayoutProperty("parques-contorno", "visibility", comParques ? "visible" : "none");
    mapa.setLayoutProperty("setores-saiu", "visibility", camada === "simulacao" ? "visible" : "none");
    legenda.innerHTML = htmlLegenda(camada, opcoes, extraLegenda);
  }

  function ligarEventos() {
    let idHover = null;
    const limparHover = () => {
      if (idHover !== null) mapa.setFeatureState({ source: "setores", id: idHover }, { hover: false });
      idHover = null;
      tooltip.style.display = "none";
      mapa.getCanvas().style.cursor = "";
    };
    mapa.on("mousemove", "setores-fill", (ev) => {
      const f = ev.features[0];
      if (!f) return;
      if (idHover !== f.id) {
        limparHover();
        idHover = f.id;
        mapa.setFeatureState({ source: "setores", id: idHover }, { hover: true });
      }
      mapa.getCanvas().style.cursor = "pointer";
      tooltip.innerHTML = `<strong>${valorTooltip(camada, f.properties, estados.get(f.id))}</strong><br><span>setor ${f.id}</span>`;
      tooltip.style.display = "block";
      // mantém o tooltip dentro do mapa
      const x = Math.min(ev.point.x + 14, el.clientWidth - tooltip.offsetWidth - 8);
      const y = Math.min(ev.point.y + 14, el.clientHeight - tooltip.offsetHeight - 8);
      tooltip.style.transform = `translate(${x}px, ${y}px)`;
    });
    mapa.on("mouseleave", "setores-fill", limparHover);
    mapa.on("click", "setores-fill", (ev) => {
      const f = ev.features[0];
      if (!f) return;
      tooltip.style.display = "none";
      new maplibregl.Popup({ maxWidth: "300px", className: "mapa-popup" })
        .setLngLat(ev.lngLat)
        .setHTML(htmlPopup(f.properties, estados.get(f.id)))
        .addTo(mapa);
    });
  }

  return {
    pronto,
    get mapa() { return mapa; },
    mostrarCamada(nome) {
      camada = nome;
      return pronto.then(aplicarCamada);
    },
    // marca no mapa um conjunto de ids no estado `chave` ("sim" ou "prio")
    definirConjunto(chave, ids) {
      estados.forEach((e, id) => { e[chave] = ids.has(id); });
      return pronto.then(() => {
        estados.forEach((e, id) => mapa.setFeatureState({ source: "setores", id }, { [chave]: e[chave] }));
      });
    },
    destacarQuintil(q) {
      return pronto.then(() =>
        mapa.setFilter("setores-destaque", ["==", ["get", "quintil"], q ?? -1]));
    },
    atualizarLegenda(extra) {
      extraLegenda = { ...extraLegenda, ...extra };
      return pronto.then(aplicarCamada);
    },
  };
}
