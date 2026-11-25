// Mírame — app local. Sin dependencias ni compilación: una página con tres vistas.
"use strict";

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const vista = $("#vista");
let ESTADO = null;          // /api/estado
let sondeo = null;          // temporizador de trabajos

// ---------------------------------------------------------------- utilidades
async function api(ruta, opciones = {}) {
  const r = await fetch(`/api/${ruta}`, {
    ...opciones,
    headers: { "Content-Type": "application/json", ...(opciones.headers || {}) },
    body: opciones.body && typeof opciones.body !== "string" && !(opciones.body instanceof Blob)
      ? JSON.stringify(opciones.body) : opciones.body,
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(datos.error || `Error ${r.status}`);
  return datos;
}
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v, d = 1) => v == null ? "—" : Number(v).toLocaleString("es", { minimumFractionDigits: d, maximumFractionDigits: d });
function hms(s) {
  if (s == null) return "—";
  s = Math.round(s);
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}` : `${m}:${String(x).padStart(2, "0")}`;
}
const tamano = mb => mb >= 1000 ? `${num(mb / 1000)} GB` : `${num(mb, 0)} MB`;
function fecha(iso) {
  if (!iso) return "";
  const d = new Date(`${iso.slice(0, 10)}T12:00:00`);
  return isNaN(d) ? iso : d.toLocaleDateString("es", { day: "numeric", month: "short", year: "numeric" });
}

function toast(texto, ms = 3500) {
  const t = $("#toast");
  t.textContent = texto; t.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, ms);
}

// Modal de confirmación: devuelve una promesa con true/false.
function confirmar({ titulo, texto, si = "Aceptar", peligro = false }) {
  const m = $("#modal");
  $("#modal-titulo").textContent = titulo;
  $("#modal-texto").innerHTML = texto;
  const bSi = $("#modal-si"), bNo = $("#modal-no");
  bSi.textContent = si;
  bSi.className = peligro ? "peligro" : "";
  m.hidden = false;
  bNo.focus();
  return new Promise(resolver => {
    const cerrar = v => { m.hidden = true; bSi.onclick = bNo.onclick = m.onclick = document.onkeydown = null; resolver(v); };
    bSi.onclick = () => cerrar(true);
    bNo.onclick = () => cerrar(false);
    m.onclick = e => { if (e.target === m) cerrar(false); };
    document.onkeydown = e => { if (e.key === "Escape") cerrar(false); };
  });
}

// ---------------------------------------------------------------- enrutador
const VISTAS = { "": verNuevo, biblioteca: verBiblioteca, ajustes: verAjustes };
async function enrutar() {
  const nombre = location.hash.replace(/^#\/?/, "").split("/")[0];
  const fn = VISTAS[nombre] || verNuevo;
  for (const a of document.querySelectorAll("[data-nav]"))
    a.classList.toggle("activo", a.dataset.nav === (nombre || "nuevo"));
  clearInterval(sondeo);
  ESTADO = await api("estado").catch(() => ESTADO);
  if (ESTADO) {
    $("#version").textContent = ESTADO.version;
    $("#carpeta-datos").textContent = `Datos en ${ESTADO.datos}`;
  }
  await fn();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", enrutar);

function plantilla(id) {
  vista.replaceChildren($(`#${id}`).content.cloneNode(true));
}

// Globo en «Biblioteca» con los trabajos en curso, en todas las vistas.
async function revisarGlobo() {
  const trabajos = await api("trabajos").catch(() => []);
  const activos = trabajos.filter(t => t.estado === "en_cola" || t.estado === "corriendo").length;
  const g = $("#globo");
  g.hidden = !activos; g.textContent = activos;
  return trabajos;
}
setInterval(revisarGlobo, 4000);

// ---------------------------------------------------------------- Nuevo análisis
const esYoutube = t => /(youtube\.com|youtu\.be)\//i.test(t);
function seg(texto) {
  // "1:02:03", "62:03", "90" → segundos; vacío o inválido → null
  const t = String(texto ?? "").trim();
  if (!t) return null;
  if (!/^\d+(:\d{1,2}){0,2}$/.test(t)) return NaN;
  return t.split(":").reduce((a, p) => a * 60 + Number(p), 0);
}

// Reproductor de vista previa: YouTube (IFrame API) o un <video> local.
let reproductor = null;
function cargarApiYoutube() {
  if (window.YT?.Player) return Promise.resolve();
  if (!cargarApiYoutube.p) cargarApiYoutube.p = new Promise((ok, mal) => {
    window.onYouTubeIframeAPIReady = ok;
    const s = document.createElement("script");
    s.src = "https://www.youtube.com/iframe_api";
    s.onerror = mal;
    document.head.appendChild(s);
    setTimeout(() => mal(new Error("sin conexión con YouTube")), 10000);
  });
  return cargarApiYoutube.p;
}
async function vistaYoutube(caja, id, miniatura) {
  caja.innerHTML = `<div id="yt"></div>`;
  try {
    await cargarApiYoutube();
    await new Promise(ok => {
      const p = new YT.Player("yt", {
        videoId: id, width: "100%", height: "100%",
        playerVars: { rel: 0, modestbranding: 1, playsinline: 1 },
        events: { onReady: ok, onError: () => { caja.innerHTML = imagenRespaldo(miniatura); reproductor = null; ok(); } },
      });
      reproductor = { ahora: () => p.getCurrentTime?.() ?? 0, ir: t => { p.seekTo(t, true); p.pauseVideo?.(); } };
    });
  } catch {
    caja.innerHTML = imagenRespaldo(miniatura);
    reproductor = null;
  }
}
const imagenRespaldo = m => (m ? `<img src="${esc(m)}" alt="">` : "") +
  `<div class="sin-vista">Este video no se puede previsualizar aquí. Escribe los tiempos a mano (mm:ss).</div>`;
function vistaLocal(caja, archivo) {
  const v = document.createElement("video");
  v.controls = true; v.preload = "metadata"; v.src = URL.createObjectURL(archivo);
  caja.replaceChildren(v);
  reproductor = { ahora: () => v.currentTime, ir: t => { v.currentTime = t; v.pause(); } };
  return new Promise(ok => { v.onloadedmetadata = () => ok(v.duration); v.onerror = () => ok(null); });
}

async function verNuevo() {
  plantilla("t-nuevo");
  reproductor = null;
  const f = $("#f-nuevo");
  const aj = ESTADO?.ajustes || {};
  const chk = f.separar_lecturas;
  $("#sugerencia-claves").hidden = !!aj.puede_transcribir;
  if (aj.puede_separar_lecturas) {
    chk.checked = true;
  } else {
    chk.disabled = true;
    $("#op-lecturas").classList.add("apagado");
    $("#lecturas-nota").innerHTML = `Necesita una clave de transcripción (Whisper). <a href="#/ajustes">Agrégala en Ajustes</a>. Sin ella el análisis funciona igual, solo que la lectura bíblica cuenta como mirar abajo.`;
  }
  const chkE = f.estructura;
  if (aj.puede_analizar_estructura) {
    chkE.checked = true;
  } else {
    chkE.disabled = true;
    $("#op-estructura").classList.add("apagado");
    $("#estructura-nota").innerHTML = `Necesita una clave de IA. <a href="#/ajustes">Agrégala en Ajustes</a>.`;
  }

  let archivo = null, info = null, ultimaConsulta = "";

  async function elegido(datos) {
    info = datos;
    $("#video-elegido").hidden = false;
    $("#paso-tramo").hidden = false;
    $("#paso-opciones").hidden = false;
    $("#video-titulo").textContent = datos.titulo || "";
    $("#video-meta").innerHTML = [datos.canal && esc(datos.canal), datos.duracion && `Dura ${hms(datos.duracion)}`,
      datos.descargado && `<span class="etiqueta listo">ya descargado</span>`].filter(Boolean).join(" · ");
    f.titulo.placeholder = datos.titulo || "El del video";
    const dur = Math.round(datos.duracion || 0);
    for (const r of [$("#r-inicio"), $("#r-fin")]) { r.max = dur; r.disabled = !dur; }
    $("#r-inicio").value = 0; $("#r-fin").value = dur;
    f.inicio.value = ""; f.fin.value = "";
    sincronizarRango();
    actualizarResumen();
  }

  async function leerEnlace() {
    const url = f.origen.value.trim();
    if (!url || url === ultimaConsulta || !esYoutube(url)) return;
    ultimaConsulta = url; archivo = null; $("#archivo-elegido").textContent = "";
    ocultarError("error-info"); $("#cargando-info").hidden = false;
    try {
      const d = await api("info", { method: "POST", body: { origen: url } });
      if (f.origen.value.trim() !== url) return;
      await elegido(d);
      vistaYoutube($("#vista-previa"), d.youtube_id, d.miniatura);
    } catch (err) {
      mostrarError("error-info", err.message);
      $("#video-elegido").hidden = $("#paso-tramo").hidden = $("#paso-opciones").hidden = true;
      info = null;
    } finally { $("#cargando-info").hidden = true; }
  }
  let espera;
  f.origen.addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(leerEnlace, 500); });
  f.origen.addEventListener("paste", () => setTimeout(leerEnlace, 50));

  $("#archivo").addEventListener("change", async e => {
    archivo = e.target.files[0] || null;
    if (!archivo) return;
    f.origen.value = ""; ultimaConsulta = "";
    $("#archivo-elegido").textContent = `${archivo.name} (${tamano(archivo.size / 1e6)})`;
    ocultarError("error-info");
    const caja = $("#vista-previa");
    const duracion = await vistaLocal(caja, archivo);
    await elegido({ titulo: archivo.name.replace(/\.[^.]+$/, ""), duracion, canal: "Archivo de tu computadora" });
  });

  // ---- tramo: todo o una parte
  for (const r of f.querySelectorAll("[name=alcance]")) r.addEventListener("change", () => {
    const tramo = f.alcance.value === "tramo";
    $("#tramo").hidden = !tramo;
    $("#nota-alcance").hidden = tramo;
    actualizarResumen();
  });
  function sincronizarRango() {
    const a = +$("#r-inicio").value, b = +$("#r-fin").value, max = +$("#r-fin").max || 1;
    const sel = $("#rango-sel");
    sel.style.left = `${a / max * 100}%`; sel.style.width = `${Math.max(0, b - a) / max * 100}%`;
  }
  function desdeRango(cual) {
    const ri = $("#r-inicio"), rf = $("#r-fin");
    if (+ri.value > +rf.value - 1) { if (cual === "inicio") ri.value = +rf.value - 1; else rf.value = +ri.value + 1; }
    f.inicio.value = +ri.value ? hms(+ri.value) : "";
    f.fin.value = +rf.value < +rf.max ? hms(+rf.value) : "";
    sincronizarRango(); actualizarResumen();
  }
  $("#r-inicio").addEventListener("input", () => desdeRango("inicio"));
  $("#r-fin").addEventListener("input", () => desdeRango("fin"));
  for (const [campo, r] of [["inicio", "#r-inicio"], ["fin", "#r-fin"]]) {
    f[campo].addEventListener("change", () => {
      const v = seg(f[campo].value);
      if (v != null && !isNaN(v)) { $(r).value = v; sincronizarRango(); }
      actualizarResumen();
    });
  }
  f.addEventListener("click", e => {
    const m = e.target.closest("[data-marcar]");
    if (m) {
      if (!reproductor) { toast("Escribe el tiempo a mano: este video no tiene vista previa."); return; }
      const t = Math.floor(reproductor.ahora());
      f[m.dataset.marcar].value = hms(t);
      $(m.dataset.marcar === "inicio" ? "#r-inicio" : "#r-fin").value = t;
      sincronizarRango(); actualizarResumen();
    }
    const ir = e.target.closest("[data-ir]");
    if (ir && reproductor) {
      const v = seg(f[ir.dataset.ir].value);
      reproductor.ir(v == null || isNaN(v) ? (ir.dataset.ir === "inicio" ? 0 : Math.max(0, (info?.duracion || 1) - 5)) : v);
    }
  });

  // ---- resumen: qué se analiza, cuánto tarda y qué conviene revisar
  function tramoElegido() {
    const tramo = f.alcance.value === "tramo";
    return { inicio: tramo ? seg(f.inicio.value) : null, fin: tramo ? seg(f.fin.value) : null };
  }
  let esperaResumen;
  function actualizarResumen() {
    clearTimeout(esperaResumen);
    esperaResumen = setTimeout(async () => {
      if (!info) return;
      const { inicio, fin } = tramoElegido();
      const caja = $("#resumen-envio"), avisos = $("#avisos");
      if (Number.isNaN(inicio) || Number.isNaN(fin)) {
        caja.textContent = ""; avisos.innerHTML = `<li class="mal">Escribe los tiempos como mm:ss o h:mm:ss.</li>`; return;
      }
      if (inicio != null && fin != null && fin <= inicio) {
        caja.textContent = ""; avisos.innerHTML = `<li class="mal">El fin debe ser después del inicio.</li>`; return;
      }
      if (info.duracion && fin != null && fin > info.duracion + 1) {
        caja.textContent = ""; avisos.innerHTML = `<li class="mal">El video dura ${hms(info.duracion)}: el fin no puede pasar de ahí.</li>`; return;
      }
      try {
        const e = await api("estimar", { method: "POST", body: {
          duracion: info.duracion, inicio: inicio != null ? String(inicio) : null, fin: fin != null ? String(fin) : null,
          fps: f.fps.value, lecturas: chk.checked, estructura: chkE.checked, descargar: !archivo && !info.descargado } });
        const desde = inicio ? ` (de ${hms(inicio)} a ${hms(fin ?? info.duracion)})` : fin ? ` (hasta ${hms(fin)})` : "";
        caja.innerHTML = info.duracion
          ? `Se analizarán <b>${hms(e.tramo)}</b>${desde}. Tardará unos <b>${Math.max(1, Math.round(e.segundos / 60))} min</b> en esta computadora.`
          : "";
        avisos.innerHTML = e.advertencias.map(a => `<li>${esc(a)}</li>`).join("");
      } catch { /* la estimación es solo orientativa */ }
    }, 250);
  }
  chk.addEventListener("change", actualizarResumen);
  chkE.addEventListener("change", actualizarResumen);
  f.fps.addEventListener("change", actualizarResumen);

  f.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarError("error-nuevo");
    const datos = Object.fromEntries(new FormData(f));
    const { inicio, fin } = tramoElegido();
    if (Number.isNaN(inicio) || Number.isNaN(fin)) return mostrarError("error-nuevo", "Revisa los tiempos del tramo (mm:ss).");
    datos.inicio = inicio != null ? String(inicio) : "";
    datos.fin = fin != null ? String(fin) : "";
    datos.separar_lecturas = chk.checked;
    datos.estructura = chkE.checked;
    datos.solo_cabeza = f.solo_cabeza.checked;
    const b = $("#b-analizar");
    b.disabled = true;
    try {
      if (archivo) {
        datos.origen = await subir(archivo, pct => { b.textContent = `Subiendo el video… ${pct} %`; });
        if (!datos.titulo) datos.titulo = archivo.name.replace(/\.[^.]+$/, "");
      }
      if (!datos.origen) throw new Error("Pega el enlace de YouTube o elige un archivo de video.");
      await api("analizar", { method: "POST", body: datos });
      location.hash = "#/biblioteca";
    } catch (err) {
      mostrarError("error-nuevo", err.message);
      b.disabled = false; b.textContent = "Analizar sermón";
    }
  });
  f.origen.focus();
}

// Subida con avance (fetch no informa el progreso de envío).
function subir(archivo, avance) {
  return new Promise((ok, mal) => {
    const x = new XMLHttpRequest();
    x.open("POST", `/api/subir?nombre=${encodeURIComponent(archivo.name)}`);
    x.upload.onprogress = e => e.lengthComputable && avance(Math.round(e.loaded / e.total * 100));
    x.onload = () => {
      let j = {};
      try { j = JSON.parse(x.responseText); } catch { /* respuesta vacía */ }
      x.status < 300 ? ok(j.ruta) : mal(new Error(j.error || "No se pudo subir el video."));
    };
    x.onerror = () => mal(new Error("La subida se cortó."));
    x.send(archivo);
  });
}

function mostrarError(id, texto) { const el = $(`#${id}`); if (el) { el.textContent = texto; el.hidden = false; } }
function ocultarError(id) { const el = $(`#${id}`); if (el) el.hidden = true; }

// ---------------------------------------------------------------- Biblioteca
async function verBiblioteca() {
  plantilla("t-biblioteca");
  await Promise.all([pintarTrabajos(), pintarLista(), pintarAlmacen()]);
  let habiaActivos = true;
  sondeo = setInterval(async () => {
    const activos = await pintarTrabajos();
    if (habiaActivos && !activos) pintarLista();   // algo terminó: refrescar la lista
    habiaActivos = activos;
  }, 1000);
}

const TIPOS_TRABAJO = { lecturas: "Separar lectura bíblica y oración", estructura: "Analizar la estructura del sermón" };
const ETAPAS = { en_cola: "En cola", corriendo: "Analizando", listo: "Listo", error: "Error", cancelado: "Cancelado" };
let ultimosTrabajos = "";

async function pintarTrabajos() {
  const trabajos = await revisarGlobo();
  const caja = $("#trabajos");
  if (!caja) return false;
  const firma = JSON.stringify(trabajos);
  if (firma !== ultimosTrabajos) {
    ultimosTrabajos = firma;
    caja.innerHTML = trabajos.map(t => {
      const activo = t.estado === "en_cola" || t.estado === "corriendo";
      const pct = t.fraccion != null ? Math.round(t.fraccion * 100) : null;
      const general = Math.round((t.general || 0) * 100);
      const etapas = (t.plan || []).map(e => {
        const hecha = t.hechas.includes(e) || t.estado === "listo";
        const actual = !hecha && e === t.etapa && t.estado === "corriendo";
        return `<li class="${hecha ? "hecha" : actual ? "actual" : ""}">${hecha ? "✓" : actual ? "●" : "○"} ${esc(e)}${actual && pct != null ? ` <b>${pct} %</b>` : ""}</li>`;
      }).join("");
      return `<div class="tarjeta trabajo ${t.estado}">
        <div class="trabajo-cabeza">
          <div>
            <div class="trabajo-titulo">${esc(t.titulo)}</div>
            <div class="trabajo-detalle">${TIPOS_TRABAJO[t.tipo] || "Nuevo análisis"}</div>
          </div>
          <div>
            <span class="etiqueta ${t.estado}">${ETAPAS[t.estado]}</span>
            ${activo ? `<button class="texto rojo chico" data-cancelar="${t.id}">Cancelar</button>` : ""}
            ${t.estado === "listo" && t.analisis ? `<a class="boton chico" href="/analisis/${encodeURIComponent(t.analisis)}/reporte.html${t.tipo === "estructura" ? "?vista=sermon" : ""}">Abrir reporte</a>` : ""}
          </div>
        </div>
        ${activo ? `<div class="barra-avance ${t.estado === "en_cola" ? "indef" : ""}"><span style="width:${general}%"></span></div>
          <div class="trabajo-detalle avance-texto"><b>${t.estado === "en_cola" ? "Esperando turno" : `${general} %`}</b>
            · ${hms(t.transcurrido)} transcurridos${t.restante != null ? ` · faltan ~${hms(t.restante)}` : ""}</div>
          ${etapas ? `<ul class="etapas">${etapas}</ul>` : ""}
          ${t.mensaje ? `<div class="trabajo-detalle">${esc(t.mensaje)}</div>` : ""}` : ""}
        ${t.estado === "listo" ? `<div class="trabajo-detalle">Terminado en ${hms(t.transcurrido)}.</div>` : ""}
        ${t.estado === "error" ? `<div class="error">${esc(t.error)}</div>` : ""}
      </div>`;
    }).join("");
  }
  return trabajos.some(t => t.estado === "en_cola" || t.estado === "corriendo");
}

document.addEventListener("click", async e => {
  const c = e.target.closest("[data-cancelar]");
  if (!c) return;
  const ok = await confirmar({ titulo: "¿Cancelar el análisis?", texto: "Se pierde lo avanzado de este trabajo.", si: "Cancelar análisis", peligro: true });
  if (ok) { await api(`trabajos/${c.dataset.cancelar}/cancelar`, { method: "POST" }); ultimosTrabajos = ""; pintarTrabajos(); }
});

async function pintarLista() {
  const lista = await api("analisis").catch(err => { toast(err.message); return []; });
  const caja = $("#lista");
  if (!caja) return;
  if (!lista.length) {
    caja.innerHTML = `<div class="tarjeta vacio">Todavía no hay análisis.<br><br><a href="#/" class="boton">Analizar el primer sermón</a></div>`;
    return;
  }
  const puedeSeparar = ESTADO?.ajustes?.puede_separar_lecturas;
  const puedeEstructura = ESTADO?.ajustes?.puede_analizar_estructura;
  caja.innerHTML = lista.map(a => {
    const listo = a.pct_congregacion != null;
    const reparto = listo ? `<div class="reparto">
        <span style="width:${a.pct_congregacion}%;background:var(--verde)"></span>
        <span style="width:${a.pct_notas ?? 0}%;background:var(--ambar)"></span>
        <span style="width:${a.pct_biblia ?? 0}%;background:var(--azul)"></span></div>` : "";
    const origen = a.origen && a.origen.startsWith("http")
      ? `<a href="${esc(a.origen)}" target="_blank" rel="noopener">YouTube</a>` : "archivo local";
    return `<div class="tarjeta analisis">
      <div>
        <div class="analisis-titulo">${esc(a.titulo)}</div>
        <div class="analisis-meta">${fecha(a.creado)} · ${hms(a.duracion)} analizados${a.inicio ? ` desde el ${hms(a.inicio)}` : ""} · ${origen} · ${tamano(a.megabytes)}
          ${a.estado !== "listo" ? ` · <span class="etiqueta ${a.estado}">${a.estado === "en_proceso" ? "En proceso" : "Incompleto"}</span>` : ""}</div>
        ${listo ? `<div class="cifras">
          <div class="cifra verde"><b class="num">${num(a.pct_congregacion)} %</b><span>congregación</span></div>
          <div class="cifra ambar"><b class="num">${num(a.pct_notas)} %</b><span>${a.pct_biblia != null ? "notas" : "abajo"}</span></div>
          ${a.pct_biblia != null ? `<div class="cifra azul"><b class="num">${num(a.pct_biblia)} %</b><span>Biblia</span></div>` : ""}
          ${a.mirada_media != null ? `<div class="cifra"><b class="num">${num(a.mirada_media)} s</b><span>por mirada</span></div>` : ""}
        </div>${reparto}` : ""}
      </div>
      <div class="analisis-acciones">
        ${a.tiene_reporte ? `<a class="boton" href="/analisis/${encodeURIComponent(a.id)}/reporte.html">Abrir reporte</a>` : ""}
        ${listo && !a.con_lecturas ? `<button class="secundario chico" data-separar="${esc(a.id)}" ${puedeSeparar ? "" : "disabled title='Agrega una clave de IA en Ajustes'"}>Separar lectura bíblica</button>` : ""}
        ${listo && a.con_estructura ? `<a class="boton secundario chico" href="/analisis/${encodeURIComponent(a.id)}/reporte.html?vista=sermon">Ver estructura</a>` : ""}
        ${listo && !a.con_estructura ? `<button class="secundario chico" data-estructura="${esc(a.id)}" ${puedeEstructura ? "" : "disabled title='Agrega una clave de IA en Ajustes'"}>Analizar estructura</button>` : ""}
        <button class="texto rojo chico" data-borrar="${esc(a.id)}" data-titulo="${esc(a.titulo)}" data-mb="${a.megabytes}">Borrar</button>
      </div>
    </div>`;
  }).join("");

  caja.onclick = async e => {
    const b = e.target.closest("[data-borrar]");
    if (b) {
      const ok = await confirmar({
        titulo: "¿Borrar este análisis?",
        texto: `<b>${esc(b.dataset.titulo)}</b><br>Se borran sus datos, el reporte, las capturas y el video recortado (${tamano(+b.dataset.mb)}). No se puede deshacer.`,
        si: "Borrar", peligro: true,
      });
      if (!ok) return;
      try { await api(`analisis/${encodeURIComponent(b.dataset.borrar)}`, { method: "DELETE" }); toast("Análisis borrado."); }
      catch (err) { toast(err.message); }
      pintarLista(); pintarAlmacen();
      return;
    }
    const s = e.target.closest("[data-separar]");
    if (s) {
      try { await api(`analisis/${encodeURIComponent(s.dataset.separar)}/lecturas`, { method: "POST" }); ultimosTrabajos = ""; pintarTrabajos(); toast("Separando la lectura bíblica…"); }
      catch (err) { toast(err.message); }
      return;
    }
    const es = e.target.closest("[data-estructura]");
    if (es) {
      try { await api(`analisis/${encodeURIComponent(es.dataset.estructura)}/estructura`, { method: "POST" }); ultimosTrabajos = ""; pintarTrabajos(); toast("Analizando la estructura del sermón…"); }
      catch (err) { toast(err.message); }
    }
  };
}

async function pintarAlmacen() {
  const caja = $("#almacen");
  if (!caja || !ESTADO) return;
  const d = (await api("estado").catch(() => ESTADO)).descargas;
  caja.innerHTML = `<span>Videos completos descargados de YouTube (caché): <b>${d.archivos}</b> · ${tamano(d.megabytes)}.
      Se reutilizan si vuelves a analizar el mismo enlace; borrarlos no afecta los análisis.</span>
    ${d.archivos ? `<button class="secundario chico" id="vaciar">Vaciar caché</button>` : ""}`;
  const b = $("#vaciar");
  if (b) b.onclick = async () => {
    const ok = await confirmar({ titulo: "¿Vaciar la caché de descargas?", texto: `Se borran ${d.archivos} videos (${tamano(d.megabytes)}). Tus análisis y reportes no se tocan.`, si: "Vaciar", peligro: true });
    if (!ok) return;
    const r = await api("descargas/vaciar", { method: "POST" });
    toast(`${r.borrados} videos borrados.`);
    pintarAlmacen();
  };
}

// ---------------------------------------------------------------- Ajustes
async function verAjustes() {
  plantilla("t-ajustes");
  const f = $("#f-ajustes");
  const aj = await api("ajustes");
  for (const k of ["groq_clave", "openai_clave", "whisper_url", "whisper_clave", "whisper_modelo", "llm_url", "llm_clave", "llm_modelo"])
    f[k].value = aj[k] || "";
  f.prov_whisper.value = aj.whisper_url ? "otro" : "groq";
  f.proveedor.value = aj.llm_url ? "otro" : "groq";
  f.api.value = aj.api || "";
  const mostrar = () => {
    const wOtro = f.prov_whisper.value === "otro", lOtro = f.proveedor.value === "otro";
    $("#whisper-otro").hidden = !wOtro;
    // La clave de Groq hace falta si cualquiera de los dos pasos usa Groq.
    $("#whisper-groq").hidden = wOtro && lOtro && f.api.value !== "groq";
    $("#otro-proveedor").hidden = !lOtro;
  };
  mostrar();
  for (const r of f.querySelectorAll("[name=prov_whisper],[name=proveedor],[name=api]")) r.addEventListener("change", mostrar);
  $("#estado-claves").innerHTML = aj.puede_separar_lecturas
    ? `<span class="etiqueta listo">Listo</span> Mírame separará la lectura bíblica y la oración${aj.puede_analizar_estructura ? ", y podrá analizar la estructura del sermón" : ""}.`
    : aj.puede_transcribir
      ? `<span class="etiqueta en_cola">Falta el paso 2</span> Ya puede transcribir; falta el modelo que marca las lecturas.`
      : `<span class="etiqueta incompleto">Sin claves</span> Mírame mide la mirada; la lectura bíblica cuenta como mirar abajo.`;
  $("#guardado-en").textContent = aj.desde_entorno?.length
    ? `Algunos valores vienen de variables de entorno y tienen prioridad: ${aj.desde_entorno.join(", ")}.`
    : `Se guardan solo en tu computadora (${ESTADO?.datos || ""}/configuracion.json).`;
  // Quién hace cada paso con lo guardado (cambia con «Qué API usar»).
  const u = aj.en_uso || {};
  $("#en-uso").textContent = u.transcripcion
    ? `Ahora transcribe con ${u.transcripcion}; marca las lecturas con ${u.lecturas || "(falta configurar)"}; analiza la estructura con ${u.estructura || "(falta configurar)"}.`
    : (aj.api ? "Falta la clave de la API elegida: sin ella no se usa la IA." : "");

  f.addEventListener("click", async e => {
    const ver = e.target.closest("[data-ver]");
    if (ver) {
      const input = f[ver.dataset.ver];
      input.type = input.type === "password" ? "text" : "password";
      ver.textContent = input.type === "password" ? "Ver" : "Ocultar";
    }
    const probar = e.target.closest("[data-probar]");
    if (probar) {
      const tipo = probar.dataset.probar;
      const caja = $(`#prueba-${tipo}`);
      caja.className = "resultado-prueba"; caja.textContent = "Probando…";
      try {
        const r = await api("ajustes/probar", { method: "POST", body: {
          tipo, groq_clave: f.groq_clave.value, openai_clave: f.openai_clave.value,
          whisper_url: f.whisper_url.value, whisper_clave: f.whisper_clave.value,
          llm_url: f.llm_url.value, llm_clave: f.llm_clave.value } });
        caja.className = `resultado-prueba ${r.ok ? "ok" : "mal"}`;
        caja.textContent = (r.ok ? "✓ " : "✗ ") + r.mensaje;
        if (r.ok && tipo === "llm") $("#modelos").innerHTML = r.modelos.map(m => `<option value="${esc(m)}">`).join("");
      } catch (err) { caja.className = "resultado-prueba mal"; caja.textContent = `✗ ${err.message}`; }
    }
  });

  f.addEventListener("submit", async e => {
    e.preventDefault();
    ocultarError("error-ajustes");
    const wOtro = f.prov_whisper.value === "otro", lOtro = f.proveedor.value === "otro";
    if (wOtro && (!f.whisper_url.value || !f.whisper_clave.value || !f.whisper_modelo.value))
      return mostrarError("error-ajustes", "Para otro servicio de transcripción completa la URL, la clave y el modelo.");
    if (lOtro && (!f.llm_url.value || !f.llm_clave.value || !f.llm_modelo.value))
      return mostrarError("error-ajustes", "Para otro proveedor de análisis completa la URL, la clave y el modelo.");
    const elegida = f.api.value;
    if (elegida && !f[`${elegida}_clave`].value)
      return mostrarError("error-ajustes", `Para usar solo ${elegida === "groq" ? "Groq" : "OpenAI"} escribe su clave.`);
    try {
      await api("ajustes", { method: "POST", body: {
        api: elegida,
        openai_clave: f.openai_clave.value,
        groq_clave: wOtro && lOtro && elegida !== "groq" ? "" : f.groq_clave.value,
        whisper_url: wOtro ? f.whisper_url.value : "", whisper_clave: wOtro ? f.whisper_clave.value : "",
        whisper_modelo: wOtro ? f.whisper_modelo.value : "",
        llm_url: lOtro ? f.llm_url.value : "", llm_clave: lOtro ? f.llm_clave.value : "",
        llm_modelo: lOtro ? f.llm_modelo.value : "",
      } });
      toast("Ajustes guardados.");
      ESTADO = await api("estado");
      verAjustes();
    } catch (err) { mostrarError("error-ajustes", err.message); }
  });
}

enrutar();
