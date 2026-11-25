const DATOS = /*DATOS*/;
const R = DATOS.resumen, P = R.parametros;
const CLASES = ["congregacion", "abajo", "sin_dato", "excluido"];
const NOMBRES = { congregacion: "Mirando a la congregación", abajo: "Mirando sus notas", sin_dato: "Sin dato", excluido: "Excluido" };
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const COLOR = { congregacion: css("--congregacion"), abajo: css("--abajo"), sin_dato: css("--sin-dato"), excluido: css("--excluido") };
const SEG = DATOS.segundos;            // [t, clase, pitch]
const LECT = DATOS.lecturas || [];     // [inicio, fin, referencia]
const B = R.biblia;
const lecturaEn = t => LECT.find(([a, b]) => t >= a && t < b);
const FOT = DATOS.fotogramas;          // [clase, pitch, x, y, w, h, ojos]
const DUR = Math.max(DATOS.duracion, SEG.length);
const params = new URLSearchParams(location.search);
const CAPTURA = params.has("captura");
const video = document.getElementById("video");
let tFijo = null;
const ahora = () => tFijo ?? video.currentTime ?? 0;

function hms(s) {
  s = Math.max(0, Math.round(s));
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}` : `${m}:${String(x).padStart(2, "0")}`;
}
const num = (v, d = 1) => v.toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d });
const seg = d => `${num(d, d >= 10 ? 0 : 1)} s`;

// ---------- Encabezado ----------
document.getElementById("titulo").textContent = DATOS.titulo;
document.getElementById("subtitulo").textContent =
  `${hms(R.video.duracion_analizada)} analizados` + (R.video.inicio ? ` desde el ${hms(R.video.inicio)} del video` : "") +
  ` · rostro visible el ${num(100 - R.pct_sin_dato, 0)} % del tiempo`;
document.getElementById("advertencias").innerHTML =
  R.advertencias.map(a => `<div class="advertencia" style="margin-bottom:14px">${a}</div>`).join("");

// ---------- Veredicto: una cifra y su reparto ----------
const partes = B ? [
  ["congregacion", R.pct_congregacion, "congregación"],
  ["abajo", B.pct_abajo_fuera_de_biblia, "sus notas"],
  ["biblia", B.pct_abajo_leyendo_biblia, "la Biblia"],
] : [
  ["congregacion", R.pct_congregacion, "congregación"],
  ["abajo", R.pct_abajo, "abajo, a las notas"],
];
document.getElementById("cifra").textContent = `${num(R.pct_congregacion)} %`;
document.getElementById("frase").textContent = "del sermón mirando a la congregación";
// Margen de error (bootstrap por bloques) y cuánto cambiaría con un umbral más estricto o más laxo.
{
  const ic = R.intervalo_congregacion, sens = R.sensibilidad ? Object.values(R.sensibilidad).filter(v => v != null) : [];
  const partes = [];
  if (ic) partes.push(`margen de error 95 %: ${num(ic[0])}–${num(ic[1])} %`);
  if (sens.length === 2) partes.push(`con umbral ${P.umbral - 3}°–${P.umbral + 3}°: ${num(Math.min(...sens))}–${num(Math.max(...sens))} %`);
  document.getElementById("margen").textContent = partes.join(" · ");
}
document.getElementById("reparto").innerHTML = partes.map(([c, v]) =>
  `<span style="width:${v}%;background:var(--${c})"></span>`).join("");
const partesEl = document.getElementById("partes");
partesEl.style.gridTemplateColumns = `repeat(${partes.length}, 1fr)`;
partesEl.innerHTML = partes.map(([c, v, n]) =>
  `<div class="parte" style="--c:var(--${c});--o:var(--${c}-oscuro)"><b class="num">${num(v)} %</b><span>${n}</span></div>`).join("");

// ---------- Detalle ----------
const mayor = B ? B.episodio_mas_largo_fuera : R.episodio_mas_largo;
const C = R.contacto, miradaMayor = C && C.mirada_mas_larga;
const datos = [
  miradaMayor && { c: "verde", v: seg(miradaMayor.duracion), n: "mirada más larga", d: `en el ${miradaMayor.minuto} · clic para ir`, t: miradaMayor.inicio },
  C && { c: "verde", v: seg(C.duracion_media), n: "media por mirada", d: `${C.miradas} miradas · mediana ${num(C.duracion_mediana)} s` },
  mayor && { c: "ambar", v: seg(mayor.duracion), n: "lectura más larga", d: `en el ${mayor.minuto} · clic para ir`, t: mayor.inicio },
  { c: "ambar", v: B ? B.episodios_fuera_de_biblia : R.episodios_abajo, n: "bajadas a las notas",
    d: `≥ 1 s · media ${num(R.duracion_media_episodio)} s` },
  P.umbral_ojos != null && R.pct_abajo_solo_ojos != null &&
    { v: `${num(R.pct_abajo_solo_ojos)} %`, n: "solo con los ojos", d: "cabeza recta, mirada abajo" },
  B && { v: B.tramos, n: "lecturas bíblicas", d: `${num(B.pct_del_sermon)} % del sermón` },
  R.oracion && { v: hms(R.oracion.segundos), n: R.oracion.tramos > 1 ? `en ${R.oracion.tramos} oraciones` : "en oración",
    d: "fuera del cálculo" },
  { v: R.vistazos, n: "vistazos (< 1 s)", d: "incluye parpadeos" },
].filter(Boolean).slice(0, 8);
document.getElementById("datos").innerHTML = datos.map(x =>
  `<div class="dato ${x.c || ""}"${x.t != null ? ` data-t="${x.t}"` : ""}><div class="v num">${x.v}</div><div class="n">${x.n}</div><div class="d">${x.d}</div></div>`).join("");
document.getElementById("datos").addEventListener("click", ev => {
  const d = ev.target.closest("[data-t]"); if (d) irA(+d.dataset.t);
});

// ---------- Pie ----------
document.getElementById("metodo").textContent =
  `MediaPipe a ${num(P.fps, P.fps % 1 ? 1 : 0)} fotogramas/s. «Abajo» = cabeza más de ${P.umbral}° por debajo de su posición habitual ` +
  `(${num(P.pitch_calibracion)}°, ${P.metodo_calibracion})` +
  (P.umbral_ojos != null ? ` u ojos bajados (≥ ${num(P.umbral_ojos, 2)})` : "") +
  `. Porcentajes sobre los segundos con rostro visible.` +
  (B ? ` Lecturas y oraciones marcadas por un modelo de lenguaje sobre la transcripción.`
     : ` Sin transcripción: la lectura bíblica cuenta como mirar abajo; con una clave de Whisper (p. ej. Groq) el resultado es más fino.`) +
  (P.metodo_version ? ` Método ${P.metodo_version}.` : "");
document.getElementById("pie-derecha").textContent = `mirame ${P.version}`;
document.getElementById("zoom-nota").textContent = `${num(P.fps, P.fps % 1 ? 1 : 0)} lecturas/s`;
document.getElementById("cinta-nota").textContent = "clic para ir a ese momento · arriba: cada segundo · abajo: inclinación de la cabeza";
document.getElementById("leyenda-biblia").hidden = !B;
document.getElementById("leyenda-oracion").hidden = !R.oracion;

// ---------- Gráficas ----------
Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
Chart.defaults.font.size = 12;
Chart.defaults.color = css("--tenue");
Chart.defaults.animation = false;

// Grados relativos a la posición habitual: 0° = mirando a la congregación.
const BASE = P.pitch_calibracion, CORTE = P.umbral;
const rel = p => p == null ? null : Math.round((p - BASE) * 10) / 10;
const yMin = -30, yMax = Math.max(Math.ceil((CORTE + 25) / 10) * 10, 40);
const franja = {
  id: "franja",
  beforeDatasetsDraw(ch) {
    const { ctx, chartArea: a, scales: { x, y } } = ch;
    const yc = y.getPixelForValue(CORTE), yfin = y.getPixelForValue(yMax);
    ctx.save();
    ctx.fillStyle = "rgba(37, 99, 235, 0.10)";
    for (const [a0, b0] of LECT) {
      const x0 = Math.max(x.getPixelForValue(a0), a.left), x1 = Math.min(x.getPixelForValue(b0), a.right);
      if (x1 > x0) ctx.fillRect(x0, a.top, Math.max(1, x1 - x0), a.bottom - a.top);
    }
    ctx.fillStyle = "rgba(245, 158, 11, 0.10)";
    ctx.fillRect(a.left, Math.min(yc, yfin), a.right - a.left, Math.abs(yfin - yc));
    ctx.setLineDash([5, 5]); ctx.lineWidth = 1.2;
    ctx.strokeStyle = "rgba(180, 83, 9, 0.7)";
    ctx.beginPath(); ctx.moveTo(a.left, yc); ctx.lineTo(a.right, yc); ctx.stroke();
    ctx.restore();
  },
};
function ejeY(titulo) {
  // Invertido: más abajo en la gráfica = cabeza más inclinada hacia abajo.
  return {
    reverse: true, min: yMin, max: yMax,
    grid: { color: "#f0eee9" }, border: { display: false },
    ticks: { callback: v => (v <= yMin || v % 20) ? "" : (v === 0 ? "0°" : `${v > 0 ? "+" : ""}${v}°`), stepSize: 10 },
    title: { display: !!titulo, text: titulo },
  };
}
const ANCHO_EJE = 44;  // misma columna del eje Y en ambas gráficas para alinear con la cinta
const gPitch = new Chart(document.getElementById("c-pitch"), {
  type: "line",
  data: { datasets: [{
    data: SEG.map(([t, c, p]) => ({ x: t + 0.5, y: rel(p) })), parsing: false, borderWidth: 1, pointRadius: 0, spanGaps: false,
    segment: { borderColor: s => (s.p1.parsed.y > CORTE || s.p0.parsed.y > CORTE) ? COLOR.abajo : COLOR.congregacion },
  }] },
  options: {
    maintainAspectRatio: false, normalized: true, layout: { padding: 0 },
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: {
      x: { type: "linear", min: 0, max: DUR, grid: { display: false }, border: { display: false },
           ticks: { callback: v => hms(v), maxTicksLimit: 12 } },
      y: { ...ejeY(), afterFit: s => { s.width = ANCHO_EJE; } },
    },
  },
  plugins: [franja],
});

const VENTANA = 60;
const gZoom = new Chart(document.getElementById("c-zoom"), {
  type: "line",
  data: { datasets: [{ data: [], parsing: false, borderWidth: 1.6, pointRadius: 0, spanGaps: false,
    segment: { borderColor: s => (s.p1.parsed.y > CORTE || s.p0.parsed.y > CORTE) ? COLOR.abajo : COLOR.congregacion } }] },
  options: {
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { enabled: false } },
    scales: {
      x: { type: "linear", grid: { display: false }, border: { display: false },
           ticks: { callback: v => hms(v), stepSize: 30, autoSkip: false } },
      y: { ...ejeY(), afterFit: s => { s.width = ANCHO_EJE; } },
    },
  },
  plugins: [franja, {
    id: "ahora",
    afterDatasetsDraw(ch) {
      const { ctx, chartArea: a, scales: { x } } = ch;
      const px = x.getPixelForValue(ahora());
      ctx.save(); ctx.strokeStyle = css("--texto"); ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke(); ctx.restore();
    },
  }],
});
let zoomDesde = null;
function actualizarZoom(t) {
  const desde = Math.max(0, Math.min(t - VENTANA, DUR - 2 * VENTANA));
  const ds = gZoom.data.datasets[0];
  if (zoomDesde === null || Math.abs(desde - zoomDesde) > 0.05) {
    zoomDesde = desde;
    const i0 = Math.max(0, Math.floor(desde * P.fps)), i1 = Math.min(FOT.length, Math.ceil((desde + 2 * VENTANA) * P.fps) + 1);
    const pts = [];
    for (let i = i0; i < i1; i++) pts.push({ x: i / P.fps, y: rel(FOT[i][1]) });
    ds.data = pts;
    gZoom.options.scales.x.min = desde;
    gZoom.options.scales.x.max = desde + 2 * VENTANA;
  }
  gZoom.update("none");
}

// ---------- Cinta: un rectángulo por segundo, alineada con el área de la gráfica ----------
const cinta = document.getElementById("c-cinta");
function areaX() {
  // Columna horizontal que ocupa el tiempo en la gráfica de inclinación.
  const a = gPitch.chartArea;
  return a ? { izq: a.left, ancho: a.right - a.left } : { izq: 0, ancho: cinta.clientWidth };
}
function dibujarCinta() {
  const dpr = window.devicePixelRatio || 1;
  const W = cinta.clientWidth, h = cinta.clientHeight;
  cinta.width = Math.round(W * dpr); cinta.height = Math.round(h * dpr);
  const ctx = cinta.getContext("2d");
  ctx.scale(dpr, dpr);
  const { izq, ancho: w } = areaX();
  ctx.fillStyle = COLOR.sin_dato; ctx.fillRect(izq, 0, w, h);
  for (const [t, c] of SEG) {
    ctx.fillStyle = CLASES[c] === "abajo" && lecturaEn(t + 0.5) ? css("--biblia") : COLOR[CLASES[c]];
    const x0 = Math.floor(izq + t / DUR * w), x1 = Math.ceil(izq + (t + 1) / DUR * w);
    ctx.fillRect(x0, 0, Math.max(1, x1 - x0), h);
  }
  ctx.fillStyle = css("--biblia");
  for (const [a, b] of LECT) ctx.fillRect(izq + a / DUR * w, 0, Math.max(2, (b - a) / DUR * w), 4);
  if (mayor) {
    const x0 = izq + mayor.inicio / DUR * w, x1 = izq + (mayor.inicio + mayor.duracion) / DUR * w;
    ctx.fillStyle = "#78350f"; ctx.fillRect(x0, h - 5, Math.max(3, x1 - x0), 5);
  }
  // La mirada más larga a la congregación, marcada debajo en verde oscuro.
  if (miradaMayor) {
    const x0 = izq + miradaMayor.inicio / DUR * w, x1 = izq + (miradaMayor.inicio + miradaMayor.duracion) / DUR * w;
    ctx.fillStyle = "#14532d"; ctx.fillRect(x0, h - 5, Math.max(3, x1 - x0), 5);
  }
}
const tiempoEnCinta = ev => { const { izq, ancho } = areaX(); return (ev.offsetX - izq) / ancho * DUR; };

// ---------- Episodios más largos ----------
const masLargos = [...R.episodios].sort((a, b) => b.duracion - a.duracion || a.inicio - b.inicio).slice(0, 5);
const epEl = document.getElementById("episodios");
epEl.innerHTML = masLargos.length
  ? (miradaMayor ? `<span>Mirada más larga:</span><button class="verde" data-t="${miradaMayor.inicio}">${seg(miradaMayor.duracion)} · ${hms(miradaMayor.inicio)}</button><span style="margin-left:10px">Notas más largas:</span>` : `<span>Notas más largas:</span>`) + masLargos.map(e => {
      const bib = lecturaEn(e.inicio + e.duracion / 2);
      return `<button data-t="${e.inicio}" class="${bib ? "biblia" : ""}" title="${bib ? "Lectura bíblica" : "Notas"}">${seg(e.duracion)} · ${hms(e.inicio)}</button>`;
    }).join("")
  : `<span>Ningún episodio de 1 s o más.</span>`;
epEl.addEventListener("click", ev => { const d = ev.target.closest("[data-t]"); if (d) irA(+d.dataset.t); });

// ---------- Sermón: estructura y contenido (si se analizó con IA) ----------
const E = DATOS.estructura;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const NOMBRE_PARTE = { introduccion: "Introducción", lectura: "Lectura del pasaje", punto: "Punto", conclusion: "Conclusión", oracion: "Oración", otro: "" };
const CORTO_PARTE = { introduccion: "Intro", lectura: "Lectura", conclusion: "Conclusión", oracion: "Oración", otro: "" };
const NOMBRE_PASAJE = { leido: "leído", citado: "citado", mencionado: "mencionado", aludido: "aludido" };
const NAV_SERMON = { estructura: "Estructura", argumento: "Argumento", evangelio: "Evangelio", aplicaciones: "Aplicaciones", pasajes: "Pasajes" };
const PARTES = E ? (E.partes || []) : [];
const ir = (x, texto) => x == null || x.inicio == null ? "" :
  `<button class="ir num" data-t="${x.inicio}" title="Ir a este momento">${esc(texto ?? x.minuto ?? hms(x.inicio))}</button>`;
const cita = t => t ? `<blockquote>«${esc(t)}»</blockquote>` : "";
const rolDe = p => p.tipo === "punto" ? `Punto ${p.numero ?? ""}`.trim() : (NOMBRE_PARTE[p.tipo] ?? "");

// Qué parte del tiempo miró a la congregación entre a y b (segundos con rostro visible).
function miradaEn(a, b) {
  let c = 0, n = 0;
  for (let i = Math.max(0, Math.floor(a)); i < Math.min(SEG.length, Math.ceil(b)); i++) {
    if (SEG[i][1] === 0) { c++; n++; } else if (SEG[i][1] === 1) n++;
  }
  return n >= 20 ? 100 * c / n : null;
}

function juicio(si, textoSi, textoNo, detalle, momento, extra = "") {
  return `<div class="juicio ${si ? "si" : "no"}"><span class="marca-juicio">${si ? "✓" : "✗"}</span>
    <div><b>${si ? textoSi : textoNo}</b>${momento ? ` ${ir(momento)}` : ""}${detalle ? `<p>${esc(detalle)}</p>` : ""}${extra}</div></div>`;
}

function htmlSermon() {
  const f = E.estructura || {}, arg = E.argumento || {}, cli = E.climax || {}, eva = E.evangelio || {};
  const intro = E.introduccion;   // los análisis anteriores a esta pregunta no la traen
  const apl = E.aplicaciones || [], pas = E.pasajes || [];
  const partes = PARTES.map((p, i) => {
    const m = miradaEn(p.inicio, p.fin ?? p.inicio);
    const rol = rolDe(p), titulo = p.titulo && p.titulo !== rol ? p.titulo : "";
    return `<li data-parte="${i}">
      ${ir(p)}
      <div>
        <div class="cab">${rol ? `<span class="rol">${esc(rol)}</span>` : ""}${titulo ? `<b>${esc(titulo)}</b>` : ""}${p.anunciado ? `<span class="sello">anunciado</span>` : ""}</div>
        ${p.resumen ? `<p>${esc(p.resumen)}</p>` : ""}
        ${p.transicion ? `<p class="transicion"><span>Transición</span> «${esc(p.transicion)}»</p>` : ""}
        ${(p.subpuntos || []).length ? `<ul class="subpuntos">${p.subpuntos.map(s => `<li>${ir(s)}<span>${esc(s.titulo)}</span></li>`).join("")}</ul>` : ""}
        <p class="meta">${p.fin != null ? `${hms(p.fin - p.inicio)} de duración` : ""}${m != null ? ` · mirando a la congregación el ${num(m, 0)} %` : ""}</p>
      </div></li>`;
  }).join("");

  // Dónde anunció o enumeró: cada señal con su minuto, y si es un punto del sermón o una lista dentro de uno.
  const anuncios = (f.anuncios || []).map(a => `<li>${ir(a)}<span>${a.cita ? `«${esc(a.cita)}»` : ""}${
    a.anuncia ? ` <span class="anuncia">→ ${esc(a.anuncia)}</span>` : ""}${
    a.es_punto ? "" : ` <span class="chip aludido">lista dentro de un punto</span>`}</span></li>`).join("");

  const aspectos = [...new Set((eva.menciones || []).map(m => m.aspecto).filter(Boolean))];
  const secciones = [
    ["estructura", "Estructura", `
      ${E.tema ? `<p class="tema">${esc(E.tema)}</p>` : ""}
      ${E.pasaje_principal ? `<p class="pasaje-principal">${esc(E.pasaje_principal)}</p>` : ""}
      ${E.resumen ? `<p>${esc(E.resumen)}</p>` : ""}
      ${juicio(f.clara, "Estructura clara", "Estructura poco clara", f.explicacion)}
      ${juicio(f.anuncia_puntos, "Anunció sus puntos", "No anunció sus puntos", f.como_los_anuncia, null,
          anuncios ? `<ul class="senales">${anuncios}</ul>` : "")}
      ${!intro ? "" : juicio(intro.hay && intro.acorde, "La introducción va acorde con el argumento",
          intro.hay ? "La introducción no va acorde con el argumento" : "No tiene introducción",
          [intro.como_introduce, intro.explicacion].filter(Boolean).join(" "), intro.hay ? intro : null)}
      <h4>Partes y transiciones</h4>
      ${partes ? `<ol class="partes-sermon">${partes}</ol>` : `<p class="vacio">No se reconocieron partes.</p>`}`],
    ["argumento", "Argumento y clímax", `
      ${juicio(arg.hay, "Desarrolla un argumento", "No desarrolla un argumento", arg.tesis)}
      ${(arg.desarrollo || []).length ? `<h4>Cómo se desarrolla</h4><ol class="pasos">${arg.desarrollo.map(x =>
        `<li>${ir(x)}<p>${esc(x.paso)}</p></li>`).join("")}</ol>` : ""}
      ${arg.valoracion ? `<p>${esc(arg.valoracion)}</p>` : ""}
      <h4>Clímax</h4>
      ${cli.hay ? `<div class="climax">${ir(cli)}<div><p>${esc(cli.descripcion)}</p>${cita(cli.cita)}</div></div>`
                : `<p class="vacio">No hay un clímax reconocible.${cli.descripcion ? " " + esc(cli.descripcion) : ""}</p>`}`],
    ["evangelio", "Evangelio", `
      ${juicio(eva.presente, "Conecta el pasaje con el evangelio", "No conecta el pasaje con el evangelio", eva.resumen)}
      ${aspectos.length ? `<p class="aspectos">${aspectos.map(a => `<span class="chip">${esc(a)}</span>`).join("")}</p>` : ""}
      ${(eva.menciones || []).length ? `<ol class="pasos">${eva.menciones.map(m =>
        `<li>${ir(m)}<div><p><span class="chip">${esc(m.aspecto)}</span> ${esc(m.como)}</p>${cita(m.cita)}</div></li>`).join("")}</ol>` : ""}`],
    ["aplicaciones", `Aplicaciones${apl.length ? ` <small>${apl.length}</small>` : ""}`,
      apl.length ? `<ol class="pasos">${apl.map(a =>
        `<li>${ir(a)}<div><p>${esc(a.aplicacion)}${a.dirigida_a ? ` <span class="para">· ${esc(a.dirigida_a)}</span>` : ""}</p>
          ${a.se_apoya_en ? `<p class="meta">Se apoya en: ${esc(a.se_apoya_en)}</p>` : ""}${cita(a.cita)}</div></li>`).join("")}</ol>`
      : `<p class="vacio">No se encontraron aplicaciones concretas a los oyentes.</p>`],
    ["pasajes", `Pasajes citados${pas.length ? ` <small>${pas.length}</small>` : ""}`,
      pas.length ? `<ol class="pasajes">${pas.map(p =>
        `<li>${ir(p)}<div><b>${esc(p.referencia)}</b> <span class="chip ${esc(p.tipo)}">${esc(NOMBRE_PASAJE[p.tipo] || p.tipo)}</span>
          ${p.nota ? `<p class="meta">${esc(p.nota)}</p>` : ""}</div></li>`).join("")}</ol>`
      : `<p class="vacio">No se encontraron pasajes citados.</p>`],
  ];
  document.getElementById("sermon-nav").innerHTML =
    secciones.map(([id]) => `<button data-seccion="${id}">${NAV_SERMON[id]}</button>`).join("") +
    `<span class="espacio"></span><button class="discreto" id="copiar-sermon" title="Copiar el análisis como texto">Copiar</button>`;
  document.getElementById("sermon-cuerpo").innerHTML =
    secciones.map(([id, t, h]) => `<section id="s-${id}"><h3>${t}</h3>${h}</section>`).join("") +
    `<p class="meta pie-sermon">Análisis hecho por un modelo de lenguaje (${esc(E.modelo || "IA")}) sobre la transcripción automática. Úsalo como punto de partida: revisa cada momento en el video.</p>`;
}

function verPestana(nombre) {
  const sermon = nombre === "sermon" && !!E;
  document.body.classList.toggle("ver-sermon", sermon);
  if (sermon && document.body.classList.contains("resumen")) document.getElementById("ver-resumen").click();
  for (const b of document.querySelectorAll("[data-pestana]")) b.classList.toggle("activa", (b.dataset.pestana === "sermon") === sermon);
  parteActual = -2;
  setTimeout(redibujar, 0);
}

// Franja de capítulos sobre la cinta: una casilla por parte del sermón, alineada con el tiempo.
function dibujarCapitulos() {
  const el = document.getElementById("capitulos");
  if (!E || !PARTES.length) { el.hidden = true; return; }
  const { izq, ancho } = areaX();
  const px = t => izq + Math.max(0, Math.min(1, t / DUR)) * ancho;
  const cli = E.climax || {};
  el.hidden = false;
  el.innerHTML = PARTES.map((p, i) => {
    const x0 = px(p.inicio), x1 = px(p.fin ?? DUR);
    const corto = p.tipo === "punto" ? `${p.numero ?? ""}` : (CORTO_PARTE[p.tipo] ?? "");
    const largo = [rolDe(p), p.titulo !== rolDe(p) ? p.titulo : ""].filter(Boolean).join(": ");
    return `<button class="${p.tipo}${i === parteActual ? " actual" : ""}" data-t="${p.inicio}" data-parte="${i}" style="left:${x0}px;width:${Math.max(2, x1 - x0 - 1)}px"
      title="${esc(`${p.minuto ?? hms(p.inicio)} · ${largo}`)}"><span>${esc(x1 - x0 > 120 && p.titulo && p.tipo === "punto" ? `${corto} · ${p.titulo}` : corto)}</span></button>`;
  }).join("") + (cli.hay && cli.inicio != null
    ? `<i class="estrella" data-t="${cli.inicio}" style="left:${px(cli.inicio)}px" title="Clímax · ${esc(cli.minuto ?? hms(cli.inicio))}">★</i>` : "");
}

let parteActual = -2;
function marcarParte(t) {
  if (!E) return;
  let i = -1;
  for (let k = 0; k < PARTES.length; k++) if (t >= PARTES[k].inicio - 0.05) i = k;
  if (i === parteActual) return;
  parteActual = i;
  for (const el of document.querySelectorAll("[data-parte]")) el.classList.toggle("actual", +el.dataset.parte === i);
}

if (E) {
  htmlSermon();
  document.getElementById("pestanas").hidden = false;
  document.getElementById("pestanas").addEventListener("click", ev => {
    const b = ev.target.closest("[data-pestana]"); if (b) verPestana(b.dataset.pestana);
  });
  // Un clic en un minuto lleva el video a ese momento y lo reproduce.
  const saltar = ev => {
    const b = ev.target.closest("[data-t]"); if (!b) return;
    irA(+b.dataset.t);
    if (!CAPTURA) video.play().catch(() => {});
  };
  document.getElementById("sermon-cuerpo").addEventListener("click", saltar);
  document.getElementById("capitulos").addEventListener("click", saltar);
  document.getElementById("sermon-nav").addEventListener("click", async ev => {
    const s = ev.target.closest("[data-seccion]");
    if (s) document.getElementById(`s-${s.dataset.seccion}`).scrollIntoView({ behavior: "smooth", block: "start" });
    const c = ev.target.closest("#copiar-sermon");
    if (c) {
      try { await navigator.clipboard.writeText(DATOS.estructura_texto || ""); c.textContent = "Copiado"; }
      catch { c.textContent = "No se pudo copiar"; }
      setTimeout(() => { c.textContent = "Copiar"; }, 2000);
    }
  });
}

// ---------- Sincronía ----------
const caja = document.getElementById("caja"), etiqueta = document.getElementById("caja-etiqueta");
const escenario = document.getElementById("escenario");

function rectVideo() {
  const W = escenario.clientWidth, H = escenario.clientHeight;
  const vw = DATOS.ancho, vh = DATOS.alto;
  const s = Math.min(W / vw, H / vh);
  return { x: (W - vw * s) / 2, y: (H - vh * s) / 2, w: vw * s, h: vh * s };
}

function pintar() {
  const t = ahora();
  const i = Math.min(FOT.length - 1, Math.max(0, Math.round(t * P.fps)));
  const f = FOT[i] || [2, null];
  const s = SEG[Math.min(SEG.length - 1, Math.floor(t))] || [0, 2, null];
  const clase = CLASES[f[0]];
  const lect = lecturaEn(t);

  if (f[2] != null && clase !== "excluido") {
    const r = rectVideo(), pad = 0.25;
    const color = clase === "abajo" && lect ? css("--biblia") : COLOR[clase];
    caja.style.display = "block";
    caja.style.left = `${r.x + (f[2] - f[4] * pad) * r.w}px`;
    caja.style.top = `${r.y + (f[3] - f[5] * pad) * r.h}px`;
    caja.style.width = `${f[4] * (1 + 2 * pad) * r.w}px`;
    caja.style.height = `${f[5] * (1 + 2 * pad) * r.h}px`;
    caja.style.borderColor = color;
    etiqueta.style.background = color;
    const d = rel(f[1]);
    etiqueta.textContent = clase === "abajo"
      ? (lect ? "Biblia" : d > CORTE ? `Notas · cabeza +${num(d, 0)}°` : "Notas · ojos")
      : "Congregación";
  } else {
    caja.style.display = "none";
  }

  const cs = CLASES[s[1]];
  const pild = document.getElementById("pildora");
  pild.className = `pildora ${cs === "abajo" && lect ? "biblia" : cs}`;
  pild.textContent = cs === "abajo" && lect ? `Leyendo la Biblia${lect[2] ? " · " + lect[2] : ""}` : NOMBRES[cs];
  const r = rel(s[2]);
  document.getElementById("pitch").textContent = r == null ? "—" : `${r > 0 ? "+" : ""}${num(r, 0)}°`;
  document.querySelector(".estado-video .inclinacion").style.display = r == null ? "none" : "";
  document.getElementById("sentido").textContent = r == null ? "" :
    (r > CORTE ? " cabeza inclinada" : cs === "abajo" ? " cabeza recta, ojos abajo" : " de su posición habitual");
  document.getElementById("reloj").innerHTML = `${hms(t)} <small>/ ${hms(DUR)}</small>`;

  colocarCursor("cur-pitch", gPitch, t);
  const { izq, ancho } = areaX();
  const cc = document.getElementById("cur-cinta");
  cc.style.display = "block";
  cc.style.left = `${izq + t / DUR * ancho - 1}px`;
  cc.style.height = `${cinta.clientHeight}px`;
  if (!document.body.classList.contains("resumen") && !document.body.classList.contains("ver-sermon")) actualizarZoom(t);
  marcarParte(t);
}
function colocarCursor(id, chart, t) {
  const el = document.getElementById(id), a = chart.chartArea;
  if (!a) return;
  el.style.display = "block";
  el.style.left = `${chart.scales.x.getPixelForValue(t) - 1}px`;
  el.style.top = `${a.top}px`;
  el.style.height = `${a.bottom - a.top}px`;
}

function bucle() {
  pintar();
  if (!video.paused && "requestVideoFrameCallback" in video) video.requestVideoFrameCallback(bucle);
  else if (!video.paused) requestAnimationFrame(bucle);
}
const btnPlay = document.getElementById("reproducir");
video.addEventListener("play", () => { btnPlay.textContent = "❚❚ Pausar"; bucle(); });
video.addEventListener("pause", () => { btnPlay.textContent = "▶ Reproducir"; pintar(); });
video.addEventListener("seeked", pintar);
video.addEventListener("loadedmetadata", pintar);

function irA(t) {
  t = Math.max(0, Math.min(DUR, t));
  tFijo = null;
  video.currentTime = t;
  pintar();
}
const clicEnGrafica = chart => ev => { const x = chart.scales.x.getValueForPixel(ev.offsetX); if (x != null) irA(x); };
document.getElementById("c-pitch").addEventListener("click", clicEnGrafica(gPitch));
document.getElementById("c-zoom").addEventListener("click", clicEnGrafica(gZoom));
cinta.addEventListener("click", ev => irA(tiempoEnCinta(ev)));

btnPlay.onclick = () => video.paused ? video.play() : video.pause();
document.getElementById("atras").onclick = () => irA(ahora() - 5);
document.getElementById("adelante").onclick = () => irA(ahora() + 5);
document.getElementById("sig-episodio").onclick = () => {
  const t = ahora();
  const e = R.episodios.find(e => e.inicio > t + 0.5 && !lecturaEn(e.inicio + e.duracion / 2));
  if (e) irA(Math.max(0, e.inicio - 2));
};
// En pantalla grande el video toma el mayor tamaño que cabe en su columna sin scroll,
// conservando la proporción; los controles quedan justo debajo.
const pantallaGrande = window.matchMedia("(min-width: 1101px)");
function ajustarVideo() {
  if (!pantallaGrande.matches) { escenario.style.width = escenario.style.height = ""; return; }
  const col = document.querySelector(".col-video"), trans = document.querySelector(".transporte");
  const extra = trans ? trans.offsetHeight + parseFloat(getComputedStyle(trans).marginTop) : 0;
  const W = col.clientWidth, H = col.clientHeight - extra, prop = DATOS.ancho / DATOS.alto;
  const w = Math.min(W, H * prop);
  escenario.style.width = `${w}px`;
  escenario.style.height = `${w / prop}px`;
}
function redibujar() { ajustarVideo(); gPitch.resize(); gZoom.resize(); dibujarCinta(); dibujarCapitulos(); pintar(); }
document.getElementById("ver-resumen").onclick = () => {
  if (!document.body.classList.contains("resumen") && document.body.classList.contains("ver-sermon")) verPestana("mirada");
  document.body.classList.toggle("resumen");
  document.getElementById("ver-resumen").textContent =
    document.body.classList.contains("resumen") ? "Volver al video" : "Resumen";
  setTimeout(redibujar, 0);
};
document.addEventListener("keydown", ev => {
  if (ev.target.tagName === "INPUT" || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if (ev.code === "Space") { ev.preventDefault(); btnPlay.click(); }
  if (ev.code === "ArrowLeft") irA(ahora() - 5);
  if (ev.code === "ArrowRight") irA(ahora() + 5);
  if (ev.key === "r") document.getElementById("ver-resumen").click();
  if (ev.key === "s" && E) verPestana(document.body.classList.contains("ver-sermon") ? "mirada" : "sermon");
});

// Capturar: con `mirame ver` lo hace el servidor (Playwright); abierto como archivo, copia el comando.
const aviso = document.getElementById("aviso");
document.getElementById("capturar").onclick = async () => {
  const t = Math.round(ahora() * 100) / 100;
  const modo = document.body.classList.contains("resumen") ? "resumen" : "momento";
  if (location.protocol.startsWith("http")) {
    aviso.textContent = "Capturando…";
    try {
      const r = await fetch(`capturar?t=${t}&modo=${modo}`, { method: "POST" });
      const j = await r.json();
      aviso.textContent = r.ok ? `Guardada: ${j.archivo}` : `Error: ${j.error}`;
    } catch (e) { aviso.textContent = `Error: ${e}`; }
  } else {
    const cmd = modo === "resumen" ? `mirame capturar "${DATOS.carpeta}" --resumen`
                                   : `mirame capturar "${DATOS.carpeta}" --en ${hms(t)}`;
    try { await navigator.clipboard.writeText(cmd); aviso.textContent = "Comando copiado: pégalo en la terminal."; }
    catch { aviso.textContent = cmd; }
  }
};

// Dentro de la app (`mirame app`) el reporte vive en /analisis/<id>/: enlace de regreso.
if (location.pathname.startsWith("/analisis/")) document.getElementById("volver").hidden = false;

// ---------- Arranque ----------
window.addEventListener("resize", () => requestAnimationFrame(redibujar));
ajustarVideo();
dibujarCinta();
dibujarCapitulos();
if (params.get("vista") === "sermon") verPestana("sermon");

if (CAPTURA) {
  document.body.classList.add("captura");
  if (params.get("modo") === "resumen") document.body.classList.add("resumen");
  tFijo = parseFloat(params.get("t") || "0");
  const img = params.get("img");
  video.remove();
  const listo = () => { redibujar(); requestAnimationFrame(() => { window.__listo = true; }); };
  if (img && params.get("modo") !== "resumen") {
    const el = document.createElement("img");
    el.className = "cuadro"; el.onload = listo; el.onerror = listo; el.src = img;
    escenario.prepend(el);
  } else listo();
} else {
  const t0 = parseFloat(params.get("t") || "0");
  if (t0) video.currentTime = t0;
  pintar();
}
