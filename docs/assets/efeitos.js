// Efeitos visuais do site: fade-in ao rolar, parallax leve e TOC escondido sobre a capa.
// Só estilo: não mexe em gráficos, mapa nem números.
// Com prefers-reduced-motion não há fade, parallax nem zoom (o CSS também desliga o zoom).
(function () {
  var reduzir = window.matchMedia("(prefers-reduced-motion: reduce)");
  var celular = window.matchMedia("(max-width: 767px)");
  var raiz = document.documentElement;

  // ---------- TOC escondido enquanto a capa ocupa a tela ----------
  var capa = document.querySelector(".capa");
  if (capa && "IntersectionObserver" in window) {
    new IntersectionObserver(function (entradas) {
      document.body.classList.toggle("na-capa", entradas[0].intersectionRatio > 0.35);
    }, { threshold: [0, 0.35, 1] }).observe(capa);
  }

  if (reduzir.matches || !("IntersectionObserver" in window)) return;

  // ---------- fade-in dos blocos ----------
  // A classe "anim" só entra com JS ativo: sem JS, nada fica invisível.
  raiz.classList.add("anim");
  var seletor = [
    "main .manchete",
    "main .virada",
    "main .achado",
    "main .acao-abertura",
    "main .condicoes",
    "main .faixa",
    "main .pull",
    "main .quarto-figure",
    "main .cell",
    "main table.tabela-numeros",
    "main .callout"
  ].join(",");
  var observador = new IntersectionObserver(function (entradas) {
    entradas.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("visivel");
        observador.unobserve(e.target);
      }
    });
  }, { threshold: 0, rootMargin: "0px 0px -8% 0px" });

  function observar() {
    document.querySelectorAll(seletor).forEach(function (el) {
      if (el.classList.contains("revelar") || el.closest(".capa")) return;
      el.classList.add("revelar");
      observador.observe(el);
    });
  }
  observar();
  // As células OJS podem surgir depois do carregamento.
  window.addEventListener("load", observar);

  // Garantia: se o observador não disparar (aba em segundo plano, navegador antigo),
  // revela o que já está na tela ao rolar e, por fim, tudo após alguns segundos.
  function revelarNaTela() {
    var limite = window.innerHeight;
    document.querySelectorAll(".revelar:not(.visivel)").forEach(function (el) {
      if (el.getBoundingClientRect().top < limite) el.classList.add("visivel");
    });
  }
  window.addEventListener("scroll", revelarNaTela, { passive: true });
  setTimeout(revelarNaTela, 1500);

  // ---------- parallax leve (desligado no celular) ----------
  var camadas = Array.prototype.slice.call(document.querySelectorAll("[data-parallax]"));
  if (!camadas.length) return;
  var pendente = false;

  function atualizar() {
    pendente = false;
    var alturaTela = window.innerHeight;
    camadas.forEach(function (el) {
      if (celular.matches) { el.style.transform = ""; return; }
      var caixa = el.parentElement.getBoundingClientRect();
      if (caixa.bottom < -200 || caixa.top > alturaTela + 200) return;
      var fator = parseFloat(el.getAttribute("data-parallax")) || 0;
      var desvio = (alturaTela / 2 - (caixa.top + caixa.height / 2)) * fator;
      el.style.transform = "translate3d(0," + desvio.toFixed(1) + "px,0)";
    });
  }
  function pedir() {
    if (!pendente) { pendente = true; window.requestAnimationFrame(atualizar); }
  }
  window.addEventListener("scroll", pedir, { passive: true });
  window.addEventListener("resize", pedir);
  atualizar();
})();
