"""Estructura y contenido del sermón, a partir de la transcripción (un modelo de lenguaje).

Es un paso opcional: necesita claves de IA (ver `config.py`). Responde a lo que alguien
que evalúa un sermón quiere ubicar rápido, cada cosa con su minuto y segundo:

- las partes del sermón y dónde está la transición a cada una;
- si la introducción prepara el argumento principal;
- si la estructura es clara y si el predicador anunció sus puntos;
- el argumento, cómo se desarrolla, y el clímax;
- cómo se conectó el pasaje con el evangelio de Cristo y qué aspectos se mencionaron;
- las aplicaciones a la congregación;
- los pasajes bíblicos citados.

El modelo señala cada momento con el número de una frase de `transcripcion.json`; los
tiempos salen de ahí, no del modelo. Produce `estructura.json` (lo que muestra el
reporte; se puede editar a mano) y `estructura.md` (lo mismo, para leer o compartir).
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from . import config
from .lecturas import FaltaLlave, consultar_json
from .progreso import Progreso
from .video import formato_tiempo

TRAMO_PASAJES = 8 * 60       # s de transcripción por consulta al buscar pasajes
SOLAPE = 30                  # s repetidos entre consultas para no cortar una cita
MISMA_CITA = 45              # s: la misma referencia repetida en menos de esto es una sola cita
EN_PARALELO = 3              # consultas simultáneas al modelo

TIPOS_PARTE = ("introduccion", "lectura", "punto", "conclusion", "oracion", "otro")
NOMBRES_PARTE = {"introduccion": "Introducción", "lectura": "Lectura del pasaje", "punto": "Punto",
                 "conclusion": "Conclusión", "oracion": "Oración", "otro": "Otro"}
TIPOS_PASAJE = ("leido", "citado", "mencionado", "aludido")   # de más a menos literal
NOMBRES_PASAJE = {"leido": "leído", "citado": "citado", "mencionado": "mencionado", "aludido": "aludido"}

COMUN = """Recibes la transcripción de un sermón en español. Cada frase viene numerada así: \
«[id] (minuto) texto». La transcripción es automática: puede tener palabras mal escritas y \
nombres bíblicos deformados; interprétalos por el contexto.

Reglas:
- Describe SOLO lo que el predicador dijo. No completes con lo que un buen sermón debería tener.
- Para señalar un momento usa SIEMPRE el id de la frase (el número entre corchetes), nunca el minuto. \
Los ids van solo en los campos «desde» y «hasta»: no los escribas dentro de los textos.
- Las citas son palabras literales del predicador, breves (una o dos frases), corrigiendo solo \
errores evidentes de transcripción.
- Escribe en español, con frases completas y concretas.
- Responde SOLO con JSON, con la forma indicada."""

INSTRUCCIONES_ESTRUCTURA = """Eres un profesor de homilética que evalúa la estructura de un sermón.

""" + COMUN + """

{
 "tema": "la idea central del sermón, en una frase",
 "pasaje_principal": "el pasaje que se predica, p. ej. «Esdras 5:1-17»; «» si no hay uno",
 "resumen": "tres o cuatro frases: de qué trata el sermón y a dónde lleva al oyente",
 "estructura": {
  "clara": true o false,
  "explicacion": "dos o tres frases: ¿podría un oyente seguir el orden del sermón y recordarlo después? ¿por qué?",
  "anuncia_puntos": true o false,
  "como_los_anuncia": "una o dos frases: cómo anunció los puntos del sermón; si solo enumeró una lista dentro de un punto, dilo; «» si no enumeró nada",
  "anuncios": [
   {"desde": id de la frase donde lo dice,
    "cita": "las palabras literales con que lo anuncia o lo enumera",
    "anuncia": "qué anuncia: el título de esa parte o de ese subpunto",
    "es_punto": true o false}
  ]
 },
 "introduccion": {
  "hay": true o false,
  "desde": id de la frase donde empieza,
  "como_introduce": "con qué abre el sermón: una historia, una pregunta, un problema, el contexto del pasaje… (una o dos frases)",
  "acorde": true o false,
  "explicacion": "una o dos frases: cómo prepara la introducción el argumento principal, o por qué no tiene que ver con él"
 },
 "partes": [
  {"tipo": "introduccion | lectura | punto | conclusion | oracion | otro",
   "titulo": "el nombre que el predicador le dio; si no la nombró, uno breve que la describa",
   "anunciado": true o false,
   "desde": id de la frase con que el predicador hace la transición a esta parte,
   "transicion": "cita literal y breve de cómo hizo la transición; «» si pasó de una parte a otra sin marcarlo",
   "resumen": "una o dos frases con lo que dice en esta parte",
   "subpuntos": [{"titulo": "…", "desde": id}]}
 ],
 "argumento": {
  "hay": true o false,
  "tesis": "lo que el sermón quiere demostrar o lograr en el oyente; «» si no hay argumento",
  "desarrollo": [{"desde": id, "paso": "qué aporta este paso y cómo se apoya en el anterior"}],
  "valoracion": "dos o tres frases: cómo avanzó el argumento, si cada paso se apoya en el anterior, si hubo saltos, repeticiones o digresiones"
 },
 "climax": {
  "hay": true o false,
  "desde": id de la frase donde empieza, "hasta": id de la frase donde termina,
  "descripcion": "por qué ese es el momento más alto del sermón y cómo se llegó a él",
  "cita": "la frase literal más representativa de ese momento"
 }
}

Criterios:
- «introduccion»: lo que el predicador dice para abrir el tema antes de entrar al cuerpo del \
sermón. Puede ir antes de la oración inicial o de la lectura del pasaje, después, o partida en \
dos por ellas: búscala desde la primera frase. Los saludos y los avisos no son introducción; \
una oración tampoco. «acorde» es true si la introducción despierta la pregunta, el problema o \
la idea que el argumento principal desarrolla después; false si habla de otra cosa que el \
sermón no retoma, o si no hay introducción. Si no la hay, dilo en «explicacion».
- «partes»: van en orden y cubren el sermón entero, desde la primera frase. Si la introducción \
empieza antes de la oración inicial, son partes distintas y la introducción va primero; si \
sigue después de la oración, esa continuación es otra parte de tipo «introduccion». «punto» es \
cada división principal del cuerpo del sermón. Un sermón sin divisiones reconocibles tiene pocas \
partes (introducción, desarrollo como «otro», conclusión): no fabriques puntos.
- «anunciado» es true solo si el predicador nombró o enumeró esa parte en voz alta \
(«lo primero que vemos…», «mi segundo punto…», «en tercer lugar…»).
- «anuncios»: cada momento en que el predicador nombra o enumera una división en voz alta \
(«hoy veremos tres cosas», «lo primero…», «número dos…», «mi tercer punto…»), en orden y con la \
frase donde lo dice. «es_punto» es true si lo que anuncia es una división principal del sermón: \
una de las «partes» de tipo «punto», o el bosquejo completo. Es false si es una lista dentro \
de una parte (tres razones, tres tácticas, tres preguntas): eso es un detalle de ese punto, no \
un punto del sermón, y va además en «subpuntos». Lista vacía si no enumeró nada.
- «anuncia_puntos» es true solo si los oyentes escucharon los puntos principales del sermón \
dichos como tales: tiene que haber al menos un anuncio con «es_punto» true. Enumerar una lista \
dentro de un punto no es anunciar los puntos del sermón. Si las divisiones existen pero hay que \
deducirlas, es false.
- «estructura.clara» puede ser true aunque no anuncie puntos (por ejemplo, si sigue el texto \
versículo a versículo con transiciones evidentes) y false aunque los anuncie (si los puntos \
se mezclan o no se desarrollan).
- «subpuntos»: solo divisiones internas claras; lista vacía si no hay.
- «argumento.hay» es true si el sermón avanza hacia una conclusión paso a paso; false si es \
una serie de observaciones sueltas. «desarrollo» recoge los pasos en orden (entre 3 y 8).
- «climax.hay» es true solo si hay un momento reconocible de máxima intensidad o al que todo \
el sermón conduce. Si el sermón es parejo de principio a fin, es false y lo explicas en \
«descripcion»."""

INSTRUCCIONES_EVANGELIO = """Eres un profesor de homilética que evalúa dos cosas en un sermón: cómo conectó el pasaje \
con el evangelio de Jesucristo y cómo lo aplicó a la congregación.

""" + COMUN + """

{
 "evangelio": {
  "presente": true o false,
  "resumen": "dos a cuatro frases: cómo llevó el predicador el pasaje a Cristo y a su evangelio; si no lo hizo, dilo sin rodeos",
  "menciones": [
   {"aspecto": "encarnación | vida | muerte | resurrección | ascensión | intercesión | reinado | segunda venida | obra | persona | otro",
    "desde": id de la frase donde empieza,
    "como": "qué dijo de Cristo y cómo lo relacionó con el pasaje",
    "cita": "frase literal"}
  ]
 },
 "aplicaciones": [
  {"desde": id de la frase donde empieza,
   "aplicacion": "qué pide, anima, consuela o advierte a los oyentes",
   "dirigida_a": "a quién se dirige: toda la congregación, creyentes, no creyentes, padres, líderes…",
   "se_apoya_en": "de qué parte del pasaje o de qué verdad expuesta sale esta aplicación; «» si no la apoya en el texto",
   "cita": "frase literal"}
 ]
}

Criterios:
- «menciones»: cada momento en que el predicador habla de la persona u obra de Cristo como \
parte del mensaje. Un mismo momento puede tocar varios aspectos: sepáralos solo si los \
desarrolla por separado; si los nombra juntos, usa el principal en «aspecto» y nombra los \
demás en «como». Aspectos:
  · encarnación: que Dios se hizo hombre; su nacimiento.
  · vida: su obediencia, su ministerio, sus enseñanzas, su ejemplo.
  · muerte: la cruz, su sacrificio, la expiación, su sangre.
  · resurrección: que venció la muerte.
  · ascensión e intercesión: que está a la diestra del Padre e intercede.
  · reinado: su señorío y su reino, presente o futuro.
  · segunda venida: su regreso, el juicio, la consumación.
  · obra: la salvación que logró, dicha en general (justificación, redención, perdón, gracia) \
sin detenerse en un hecho concreto.
  · persona: quién es (su deidad, sus oficios, sus títulos).
- NO cuentan las menciones de paso: «en el nombre de Jesús» al orar, «hermanos en Cristo», \
saludos o muletillas. Tampoco hablar de Dios en general sin referirse a Cristo.
- «evangelio.presente» es true solo si el sermón explica o proclama algo de la obra de Cristo. \
Si solo lo nombra de paso, es false y «menciones» va vacía.
- «aplicaciones»: cada llamado concreto a los oyentes a creer, hacer, dejar de hacer, sentir o \
esperar algo. No cuentan la explicación del texto ni las ilustraciones en sí. Agrupa en una \
sola las frases seguidas que insisten en lo mismo. Van en orden.
- Listas vacías si no hay."""

INSTRUCCIONES_PASAJES = """Eres un asistente que registra cada pasaje de la Biblia que un predicador cita en su sermón.

""" + COMUN + """

{"pasajes": [
 {"desde": id de la frase donde empieza la cita,
  "referencia": "libro, capítulo y versículos, con el nombre del libro completo: «Esdras 5:1-2», «1 Corintios 15:3-4», «Salmo 23»",
  "tipo": "leido | citado | mencionado | aludido",
  "nota": "en pocas palabras, para qué lo usa"}
]}

Criterios:
- «leido»: lee el texto bíblico en voz alta, tal cual o casi.
- «citado»: dice de memoria palabras del texto, con o sin la referencia.
- «mencionado»: da la referencia o nombra el pasaje sin decir sus palabras («como vimos en \
Hageo 1», «abramos en Esdras 5»).
- «aludido»: se refiere a una historia o enseñanza bíblica reconocible sin dar la referencia. \
Inclúyelo solo si estás seguro de qué pasaje es.
- Registra cada vez que aparece un pasaje, aunque se repita más adelante. Si sigue leyendo el \
mismo pasaje en frases seguidas, es un solo elemento, con el rango completo de versículos.
- Si lee el pasaje versículo por versículo intercalando comentarios, registra cada versículo \
en la frase donde lo lee.
- Si no dice el versículo pero lo reconoces por las palabras, da la referencia completa. Si \
no sabes cuál es, omítelo.
- Lista vacía si no hay."""


# ---------------------------------------------------------------- consultas
def _listado(frases: list[dict], ids) -> str:
    return "\n".join(f"[{i}] ({formato_tiempo(frases[i]['inicio'])}) {frases[i]['texto']}" for i in ids)


def _tramos(frases: list[dict]) -> list[list[int]]:
    """Ids de frases por ventana de TRAMO_PASAJES segundos, con SOLAPE al inicio de cada una."""
    tramos, a, fin_total = [], 0.0, frases[-1]["fin"]
    while a < fin_total:
        b = a + TRAMO_PASAJES
        ids = [i for i, f in enumerate(frases) if f["inicio"] < b and f["fin"] > a - SOLAPE]
        if ids:
            tramos.append(ids)
        a = b
    return tramos


def analizar(carpeta: Path, progreso: Progreso | None = None) -> dict:
    """transcripcion.json → estructura.json y estructura.md."""
    progreso = progreso or Progreso()
    ruta = carpeta / "transcripcion.json"
    if not ruta.exists():
        raise FileNotFoundError("Falta transcripcion.json: primero hay que transcribir el sermón.")
    frases = json.loads(ruta.read_text())["frases"]
    if not frases:
        raise RuntimeError("La transcripción está vacía: no hay nada que analizar.")
    servicio = config.cargar().modelo_estructura()
    if servicio is None:
        raise FaltaLlave("Falta configurar el modelo para analizar el sermón. Revísalo en Ajustes.")
    url, llave, modelo = servicio

    titulo = _titulo(carpeta)
    cabecera = (f"Título del video: {titulo}\n" if titulo else "") + \
        f"Duración: {formato_tiempo(frases[-1]['fin'])}\n\nTranscripción:\n"
    completo = cabecera + _listado(frases, range(len(frases)))
    consultas = [("estructura", INSTRUCCIONES_ESTRUCTURA, completo),
                 ("evangelio", INSTRUCCIONES_EVANGELIO, completo)]
    consultas += [("pasajes", INSTRUCCIONES_PASAJES, _listado(frases, ids)) for ids in _tramos(frases)]

    progreso.aviso(f"{len(frases)} frases · {len(consultas)} consultas a {modelo}", 0.0)
    respuestas: dict[str, list[dict]] = {"estructura": [], "evangelio": [], "pasajes": []}
    ejecutor = ThreadPoolExecutor(max_workers=EN_PARALELO)
    try:
        pendientes = {ejecutor.submit(consultar_json, url, llave, modelo, instrucciones, texto, progreso): nombre
                      for nombre, instrucciones, texto in consultas}
        for n, futuro in enumerate(as_completed(pendientes), 1):
            respuestas[pendientes[futuro]].append(futuro.result())
            progreso.aviso(f"{n} de {len(consultas)} consultas listas", n / len(consultas))
    finally:
        ejecutor.shutdown(wait=False, cancel_futures=True)

    datos = normalizar(respuestas["estructura"][0], respuestas["evangelio"][0], respuestas["pasajes"], frases)
    datos = {"modelo": modelo, "generado": date.today().isoformat(), **datos}
    guardar(carpeta, datos)
    return datos


def guardar(carpeta: Path, datos: dict) -> None:
    (carpeta / "estructura.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n")
    (carpeta / "estructura.md").write_text(texto(datos, _titulo(carpeta)) + "\n")


def leer(carpeta: Path) -> dict | None:
    ruta = carpeta / "estructura.json"
    if not ruta.exists():
        return None
    try:
        datos = json.loads(ruta.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return datos if isinstance(datos, dict) and isinstance(datos.get("partes"), list) else None


def _titulo(carpeta: Path) -> str:
    try:
        return json.loads((carpeta / "resumen.json").read_text())["video"].get("titulo") or ""
    except (OSError, json.JSONDecodeError, KeyError):
        return ""


# ---------------------------------------------------------------- normalizar
def _frase(frases: list[dict], valor) -> dict | None:
    """La frase que el modelo señaló con su id, o None si el id no existe."""
    if isinstance(valor, bool) or valor is None:
        return None
    try:
        i = int(str(valor).strip().strip("[]"))
    except ValueError:
        return None
    return frases[i] if 0 <= i < len(frases) else None


IDS_EN_TEXTO = re.compile(r"\s*\[\d+(\s*[-–,y]\s*\d+)*\]")
COMILLAS = "«»\"“”"


def _txt(valor, largo: int = 700) -> str:
    """Texto del modelo en una línea, sin ids de frase sueltos ni comillas alrededor."""
    if valor is None or isinstance(valor, (dict, list)):
        return ""
    t = " ".join(IDS_EN_TEXTO.sub("", str(valor)).split()).strip(COMILLAS + " ")
    for abre, cierra in ("«»", "“”"):
        if t.count(abre) != t.count(cierra):     # quedó una comilla sin pareja al quitar las de los extremos
            t = t.replace(abre, "").replace(cierra, "")
    if t.count('"') % 2:
        t = t.replace('"', "")
    return t if len(t) <= largo else t[:largo].rsplit(" ", 1)[0] + "…"


def _si(valor) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() in ("true", "sí", "si", "yes", "1")
    return bool(valor)


def _lista(valor) -> list[dict]:
    return [x for x in valor if isinstance(x, dict)] if isinstance(valor, list) else []


def _dic(valor) -> dict:
    return valor if isinstance(valor, dict) else {}


def _momento(frase: dict) -> dict:
    return {"inicio": frase["inicio"], "minuto": formato_tiempo(frase["inicio"])}


def _sin_acentos(t: str) -> str:
    return t.lower().translate(str.maketrans("áéíóúü", "aeiouu"))


def normalizar(estructura: dict, evangelio: dict, pasajes: list[dict], frases: list[dict]) -> dict:
    """Las respuestas del modelo → el contenido de estructura.json: ids de frase convertidos
    a segundos, listas ordenadas y sin elementos que apunten a frases que no existen."""
    fin_total = frases[-1]["fin"] if frases else 0.0
    estructura, evangelio = _dic(estructura), _dic(evangelio)

    # ---- partes
    partes, vistos = [], set()
    for p in _lista(estructura.get("partes")):
        f = _frase(frases, p.get("desde"))
        if f is None or f["inicio"] in vistos:
            continue
        vistos.add(f["inicio"])
        tipo = _sin_acentos(_txt(p.get("tipo")))
        tipo = tipo if tipo in TIPOS_PARTE else "otro"
        sub = []
        for s in _lista(p.get("subpuntos")):
            fs = _frase(frases, s.get("desde"))
            if fs is not None and _txt(s.get("titulo")):
                sub.append({**_momento(fs), "titulo": _txt(s.get("titulo"), 200)})
        partes.append({**_momento(f), "tipo": tipo, "numero": None,
                       "titulo": _txt(p.get("titulo"), 200) or NOMBRES_PARTE[tipo],
                       "anunciado": _si(p.get("anunciado")), "transicion": _txt(p.get("transicion"), 400),
                       "resumen": _txt(p.get("resumen")), "subpuntos": sorted(sub, key=lambda s: s["inicio"])})
    partes.sort(key=lambda p: p["inicio"])
    numero = 0
    for i, p in enumerate(partes):
        p["fin"] = partes[i + 1]["inicio"] if i + 1 < len(partes) else max(fin_total, p["inicio"])
        if p["tipo"] == "punto":
            numero += 1
            p["numero"] = numero
        p["subpuntos"] = [s for s in p["subpuntos"] if p["inicio"] <= s["inicio"] < max(p["fin"], p["inicio"] + 1)]

    # ---- introducción
    intro = _dic(estructura.get("introduccion"))
    f = _frase(frases, intro.get("desde"))
    hay_intro = _si(intro.get("hay"))
    introduccion = {"hay": hay_intro, "inicio": None, "minuto": None,
                    "como_introduce": _txt(intro.get("como_introduce")) if hay_intro else "",
                    "acorde": hay_intro and _si(intro.get("acorde")), "explicacion": _txt(intro.get("explicacion"))}
    if hay_intro and f is not None:
        introduccion.update(_momento(f))

    # ---- estructura
    e = _dic(estructura.get("estructura"))
    anuncios = []
    for an in _lista(e.get("anuncios")):
        f = _frase(frases, an.get("desde"))
        if f is not None and (_txt(an.get("cita")) or _txt(an.get("anuncia"))):
            anuncios.append({**_momento(f), "cita": _txt(an.get("cita"), 400), "anuncia": _txt(an.get("anuncia"), 200),
                             "es_punto": _si(an.get("es_punto"))})
    anuncios.sort(key=lambda x: x["inicio"])
    # El veredicto sale de las señales: enumerar una lista dentro de un punto no es anunciar los puntos.
    anuncia = _si(e.get("anuncia_puntos")) and (not anuncios or any(x["es_punto"] for x in anuncios))
    forma = {"clara": _si(e.get("clara")), "explicacion": _txt(e.get("explicacion")),
             "anuncia_puntos": anuncia, "como_los_anuncia": _txt(e.get("como_los_anuncia")), "anuncios": anuncios}

    # ---- argumento y clímax
    a = _dic(estructura.get("argumento"))
    pasos = []
    for paso in _lista(a.get("desarrollo")):
        f = _frase(frases, paso.get("desde"))
        if f is not None and _txt(paso.get("paso")):
            pasos.append({**_momento(f), "paso": _txt(paso.get("paso"))})
    argumento = {"hay": _si(a.get("hay")), "tesis": _txt(a.get("tesis")),
                 "desarrollo": sorted(pasos, key=lambda x: x["inicio"]), "valoracion": _txt(a.get("valoracion"))}

    c = _dic(estructura.get("climax"))
    f0, f1 = _frase(frases, c.get("desde")), _frase(frases, c.get("hasta"))
    climax = {"hay": _si(c.get("hay")), "inicio": None, "fin": None, "minuto": None,
              "descripcion": _txt(c.get("descripcion")), "cita": _txt(c.get("cita"), 400)}
    if climax["hay"] and f0 is not None:
        climax.update(_momento(f0), fin=max(f1["fin"] if f1 is not None else f0["fin"], f0["fin"]))

    # ---- evangelio
    g = _dic(evangelio.get("evangelio"))
    menciones = []
    for m in _lista(g.get("menciones")):
        f = _frase(frases, m.get("desde"))
        if f is not None and (_txt(m.get("como")) or _txt(m.get("cita"))):
            menciones.append({**_momento(f), "aspecto": _txt(m.get("aspecto"), 60).lower() or "otro",
                              "como": _txt(m.get("como")), "cita": _txt(m.get("cita"), 400)})
    menciones.sort(key=lambda x: x["inicio"])
    conexion = {"presente": _si(g.get("presente")) and bool(menciones or _txt(g.get("resumen"))),
                "resumen": _txt(g.get("resumen")), "menciones": menciones}

    # ---- aplicaciones
    aplicaciones = []
    for ap in _lista(evangelio.get("aplicaciones")):
        f = _frase(frases, ap.get("desde"))
        if f is not None and _txt(ap.get("aplicacion")):
            aplicaciones.append({**_momento(f), "aplicacion": _txt(ap.get("aplicacion")),
                                 "dirigida_a": _txt(ap.get("dirigida_a"), 120),
                                 "se_apoya_en": _txt(ap.get("se_apoya_en"), 400), "cita": _txt(ap.get("cita"), 400)})
    aplicaciones.sort(key=lambda x: x["inicio"])

    return {
        "tema": _txt(estructura.get("tema")), "pasaje_principal": _txt(estructura.get("pasaje_principal"), 120),
        "resumen": _txt(estructura.get("resumen"), 1200), "estructura": forma,
        "introduccion": introduccion, "partes": partes,
        "argumento": argumento, "climax": climax, "evangelio": conexion, "aplicaciones": aplicaciones,
        "pasajes": _pasajes(pasajes, frases),
    }


def _clave_referencia(referencia: str) -> str:
    return re.sub(r"[^a-z0-9:,-]+", "", _sin_acentos(referencia).replace("–", "-").replace("—", "-"))


def _pasajes(respuestas: list[dict], frases: list[dict]) -> list[dict]:
    """Une las citas de todas las ventanas. La misma referencia repetida en menos de
    MISMA_CITA segundos (el solape entre ventanas, o el modelo que la partió en dos) es
    una sola: queda la primera, con el tipo más literal."""
    candidatos = []
    for r in respuestas:
        for p in _lista(_dic(r).get("pasajes")):
            f = _frase(frases, p.get("desde"))
            referencia = _txt(p.get("referencia"), 120)
            if f is None or not referencia:
                continue
            tipo = _sin_acentos(_txt(p.get("tipo")))
            candidatos.append({**_momento(f), "referencia": referencia,
                               "tipo": tipo if tipo in TIPOS_PASAJE else "mencionado", "nota": _txt(p.get("nota"), 300)})
    candidatos.sort(key=lambda p: (p["inicio"], TIPOS_PASAJE.index(p["tipo"])))
    salida: list[dict] = []
    ultimo: dict[str, dict] = {}
    for p in candidatos:
        clave = _clave_referencia(p["referencia"])
        previo = ultimo.get(clave)
        if previo is not None and p["inicio"] - previo["inicio"] < MISMA_CITA:
            if TIPOS_PASAJE.index(p["tipo"]) < TIPOS_PASAJE.index(previo["tipo"]):
                previo["tipo"] = p["tipo"]
            previo["nota"] = previo["nota"] or p["nota"]
            continue
        ultimo[clave] = p
        salida.append(p)
    return salida


# ---------------------------------------------------------------- texto
def texto(e: dict, titulo: str = "") -> str:
    """El análisis en Markdown: lo que imprime `mirame estructura` y lo que guarda estructura.md."""
    def si_no(v):
        return "Sí" if v else "No"

    forma, arg, cli, eva = e["estructura"], e["argumento"], e["climax"], e["evangelio"]
    lineas = [f"# {titulo}" if titulo else "# Estructura del sermón", ""]
    if e.get("tema"):
        lineas.append(f"**Tema:** {e['tema']}")
    if e.get("pasaje_principal"):
        lineas.append(f"**Pasaje principal:** {e['pasaje_principal']}")
    if e.get("resumen"):
        lineas += ["", e["resumen"]]

    lineas += ["", "## Estructura", "",
               f"- **¿Estructura clara?** {si_no(forma['clara'])}." + (f" {forma['explicacion']}" if forma["explicacion"] else ""),
               f"- **¿Anunció sus puntos?** {si_no(forma['anuncia_puntos'])}."
               + (f" {forma['como_los_anuncia']}" if forma["como_los_anuncia"] else "")]
    for an in forma.get("anuncios", []):     # los análisis anteriores no traen las señales
        lineas.append(f"  - {an['minuto']} · " + (f"«{an['cita']}»" if an["cita"] else "")
                      + (f" → {an['anuncia']}" if an["anuncia"] else "")
                      + ("" if an["es_punto"] else " *(lista dentro de un punto)*"))
    intro = e.get("introduccion")       # los análisis anteriores a esta pregunta no la traen
    if intro:
        if intro["hay"]:
            detalle = " ".join(x for x in (intro["como_introduce"], intro["explicacion"]) if x)
            lineas.append(f"- **¿La introducción va acorde con el argumento?** {si_no(intro['acorde'])}."
                          + (f" ({intro['minuto']})" if intro["minuto"] else "") + (f" {detalle}" if detalle else ""))
        else:
            lineas.append("- **Introducción:** no tiene." + (f" {intro['explicacion']}" if intro["explicacion"] else ""))
    lineas.append("")
    for p in e["partes"]:
        nombre = f"Punto {p['numero']}" if p["tipo"] == "punto" else NOMBRES_PARTE[p["tipo"]]
        titulo_parte = "" if p["titulo"] == NOMBRES_PARTE[p["tipo"]] else f": {p['titulo']}"
        lineas.append(f"- **{p['minuto']}** · {nombre}{titulo_parte}" + (" *(anunciado)*" if p["anunciado"] else ""))
        if p["resumen"]:
            lineas.append(f"  - {p['resumen']}")
        if p["transicion"]:
            lineas.append(f"  - Transición: «{p['transicion']}»")
        for s in p["subpuntos"]:
            lineas.append(f"  - {s['minuto']} · {s['titulo']}")

    lineas += ["", "## Argumento", ""]
    if arg["hay"]:
        if arg["tesis"]:
            lineas += [f"**Tesis:** {arg['tesis']}", ""]
        lineas += [f"- **{x['minuto']}** · {x['paso']}" for x in arg["desarrollo"]]
        if arg["valoracion"]:
            lineas += ["", arg["valoracion"]]
    else:
        lineas.append("El sermón no desarrolla un argumento que avance paso a paso."
                      + (f" {arg['valoracion']}" if arg["valoracion"] else ""))

    lineas += ["", "## Clímax", ""]
    if cli["hay"]:
        lineas.append((f"**{cli['minuto']}** · " if cli["minuto"] else "") + cli["descripcion"])
        if cli["cita"]:
            lineas.append(f"> {cli['cita']}")
    else:
        lineas.append("No hay un clímax reconocible." + (f" {cli['descripcion']}" if cli["descripcion"] else ""))

    lineas += ["", "## Conexión con el evangelio", ""]
    lineas.append(eva["resumen"] or ("" if eva["presente"] else "El sermón no conecta el pasaje con el evangelio de Cristo."))
    if eva["menciones"]:
        lineas.append("")
    for m in eva["menciones"]:
        lineas.append(f"- **{m['minuto']}** · {m['aspecto'].capitalize()}: {m['como']}" + (f" «{m['cita']}»" if m["cita"] else ""))

    lineas += ["", "## Aplicaciones a la congregación", ""]
    if not e["aplicaciones"]:
        lineas.append("No se encontraron aplicaciones concretas a los oyentes.")
    for ap in e["aplicaciones"]:
        lineas.append(f"- **{ap['minuto']}** · {ap['aplicacion']}" + (f" *({ap['dirigida_a']})*" if ap["dirigida_a"] else ""))
        if ap["se_apoya_en"]:
            lineas.append(f"  - Se apoya en: {ap['se_apoya_en']}")
        if ap["cita"]:
            lineas.append(f"  - «{ap['cita']}»")

    lineas += ["", "## Pasajes citados", ""]
    if not e["pasajes"]:
        lineas.append("No se encontraron pasajes citados.")
    for p in e["pasajes"]:
        lineas.append(f"- **{p['minuto']}** · {p['referencia']} ({NOMBRES_PASAJE[p['tipo']]})" + (f": {p['nota']}" if p["nota"] else ""))
    return "\n".join(lineas)
