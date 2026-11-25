"""Transcripción (Whisper en Groq u OpenAI) y marcas de lectura bíblica y oración (un modelo de lenguaje).

Es un paso opcional: necesita claves de IA (ver `config.py`). Habla con APIs
compatibles con OpenAI usando solo la biblioteca estándar.

Archivos que produce en la carpeta del análisis:
- `transcripcion.json`: frases con su segundo de inicio y fin.
- `lecturas.json`: tramos de lectura bíblica y de oración. Se puede editar a mano.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from . import config
from .herramientas import ffmpeg
from .progreso import Progreso
from .video import duracion, formato_tiempo

TRAMO_AUDIO = 20 * 60        # s por envío a Whisper (mantiene cada archivo muy por debajo de 25 MB)
TRAMO_MINIMO = 40            # s: un tramo en bucle se parte en mitades hasta llegar a este tamaño
TRAMO_TEXTO = 8 * 60         # s de transcripción por consulta al modelo
SOLAPE = 30                  # s repetidos entre consultas para no cortar una lectura


class FaltaLlave(RuntimeError):
    pass


def _pedir(url: str, llave: str, cuerpo: bytes, tipo: str, progreso: Progreso | None = None,
           intentos: int = 4) -> dict:
    for n in range(intentos):
        req = urllib.request.Request(url, data=cuerpo, method="POST", headers={
            "Authorization": f"Bearer {llave}", "Content-Type": tipo, "User-Agent": "mirame"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503) and n < intentos - 1:
                espera = float(e.headers.get("retry-after") or 0) or 15 * (n + 1)
                if progreso:
                    progreso.aviso(f"El servicio respondió {e.code}; reintento en {espera:.0f} s")
                time.sleep(espera)
                continue
            if e.code in (401, 403):
                raise FaltaLlave(f"La clave fue rechazada ({e.code}). Revísala en Ajustes.") from None
            raise RuntimeError(f"HTTP {e.code} de {url}: {detalle}") from None
        except urllib.error.URLError as e:
            if n < intentos - 1:
                time.sleep(5 * (n + 1))
                continue
            raise RuntimeError(f"No se pudo conectar con {url}: {e.reason}") from None
    raise RuntimeError("sin respuesta")


def probar(url: str, llave: str) -> list[str]:
    """Lista los modelos disponibles; sirve para comprobar una clave."""
    req = urllib.request.Request(f"{url.rstrip('/')}/models",
                                 headers={"Authorization": f"Bearer {llave}", "User-Agent": "mirame"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return sorted(m["id"] for m in json.loads(r.read()).get("data", []))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise FaltaLlave("La clave fue rechazada.") from None
        raise RuntimeError(f"HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"No se pudo conectar: {e.reason}") from None


# ---------------------------------------------------------------- transcripción
def _multipart(campos: dict, archivo: Path) -> tuple[bytes, str]:
    limite = uuid.uuid4().hex
    partes = []
    for k, v in campos.items():
        for valor in (v if isinstance(v, list) else [v]):
            partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{valor}\r\n'.encode())
    partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="{archivo.name}"\r\n'
                  f"Content-Type: audio/mpeg\r\n\r\n".encode() + archivo.read_bytes() + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


MAX_FRASE = 8.0   # s: Whisper a veces junta lectura y comentario en una frase de 30 s


def _partir(segmentos: list, palabras: list, desfase: float) -> list[dict]:
    """Frases cortas: cada segmento de Whisper se corta en pausas, en puntos o al pasar
    de MAX_FRASE segundos, usando el tiempo de cada palabra."""
    salida = []
    for sg in segmentos:
        ps = [w for w in palabras if w["start"] >= sg["start"] - 0.05 and w["end"] <= sg["end"] + 0.05]
        if sg["end"] - sg["start"] <= MAX_FRASE or not ps:
            trozos = [(sg["start"], sg["end"], sg["text"].strip())]
        else:
            trozos, actual = [], []
            for i, w in enumerate(ps):
                actual.append(w)
                sig = ps[i + 1] if i + 1 < len(ps) else None
                largo = w["end"] - actual[0]["start"]
                cortar = (sig is None or sig["start"] - w["end"] > 0.6
                          or (w["word"].rstrip().endswith((".", "?", "!", ";", ":")) and largo > 2)
                          or largo > MAX_FRASE)
                if cortar:
                    trozos.append((actual[0]["start"], w["end"], " ".join(x["word"].strip() for x in actual)))
                    actual = []
        for a, b, texto in trozos:
            if texto:
                salida.append({"inicio": round(desfase + a, 2), "fin": round(desfase + b, 2), "texto": texto})
    return salida


# Frases que Whisper inventa sobre silencio o música: vienen de los subtítulos y las
# sesiones parlamentarias con que se entrenó.
INVENTADAS = re.compile(r"amara\.org|subt[ií]tulos\s+(\w+\s+)?por\b|gracias por ver|suscr[ií]b(ete|anse)"
                        r"|señor(a|es|as)? diputad|señor presidente", re.I)


PERIODO_MAXIMO = 8           # palabras: un bucle repite una y otra vez un grupo de hasta este tamaño
MARGEN_BUCLE = 5.0           # s que se repiten antes y después de un bucle al volver a transcribirlo


def _palabras(texto: str) -> list[str]:
    return re.findall(r"\w+", texto.lower())


def _bucles(frases: list[dict]) -> set[int]:
    """Índices de las frases donde Whisper se quedó repitiendo lo mismo («y la humanidad,
    y la humanidad, y la humanidad…»). Pasa sobre silencio o música, y arrastra el error.

    Busca, palabra por palabra, un grupo de hasta PERIODO_MAXIMO palabras repetido al menos
    cuatro veces seguidas. Una repetición retórica («santo, santo, santo») no llega a eso."""
    secuencia = [(palabra, i) for i, f in enumerate(frases) for palabra in _palabras(f["texto"])]
    malas: set[int] = set()
    for periodo in range(1, PERIODO_MAXIMO + 1):
        minimo = max(3 * periodo, 8)        # coincidencias seguidas: cuatro vueltas del grupo
        racha = 0
        for k in range(periodo, len(secuencia) + 1):
            if k < len(secuencia) and secuencia[k][0] == secuencia[k - periodo][0]:
                racha += 1
                continue
            if racha >= minimo:
                malas.update(i for _, i in secuencia[k - racha - periodo:k])
            racha = 0
    return malas


def _en_bucle(frases: list[dict]) -> bool:
    return bool(_bucles(frases))


REPETICION = re.compile(r"\b(\w+(?:\W+\w+){0,7}?)(?:\W+\1\b){2,}", re.I)


def _sin_repeticiones(frases: list[dict], malas: set[int]) -> list[dict]:
    """Lo que queda de un bucle que no se pudo evitar: cada grupo repetido, una sola vez."""
    salida: list[dict] = []
    for i, f in enumerate(frases):
        if i not in malas:
            salida.append(f)
            continue
        texto = REPETICION.sub(r"\1", f["texto"]).strip(" ,")
        previo = _palabras(salida[-1]["texto"]) if salida else []
        if len(_palabras(texto)) > PERIODO_MAXIMO or (texto and _palabras(texto) != previo[-len(_palabras(texto)):]):
            salida.append({**f, "texto": texto})
    return salida


def _pedir_tramo(video: Path, inicio: float, largo: float, servicio: tuple[str, str, str], tmp: Path,
                 progreso: Progreso) -> list[dict]:
    url, llave, modelo = servicio
    mp3 = tmp / f"a{int(inicio * 10)}-{int(largo * 10)}.mp3"
    subprocess.run([ffmpeg(), "-v", "error", "-y", "-ss", str(inicio), "-t", str(largo),
                    "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k", str(mp3)],
                   check=True)
    cuerpo, tipo = _multipart({"model": modelo, "language": "es",
                               "response_format": "verbose_json",
                               "timestamp_granularities[]": ["segment", "word"],
                               "temperature": "0"}, mp3)
    r = _pedir(f"{url}/audio/transcriptions", llave, cuerpo, tipo, progreso)
    return _partir(r.get("segments", []), r.get("words", []), inicio)


def _tramo(video: Path, inicio: float, largo: float, servicio: tuple[str, str, str], tmp: Path,
           progreso: Progreso) -> list[dict]:
    """Transcribe video[inicio, inicio + largo). Si Whisper entra en bucle, vuelve a pedir
    solo la parte dañada, cada vez en pedazos más cortos: el daño queda encerrado en el
    pedazo donde empieza y lo demás se recupera."""
    frases = _pedir_tramo(video, inicio, largo, servicio, tmp, progreso)
    malas = _bucles(frases)
    if malas and largo > TRAMO_MINIMO:
        a = max(inicio, frases[min(malas)]["inicio"] - MARGEN_BUCLE)
        b = min(inicio + largo, frases[max(malas)]["fin"] + MARGEN_BUCLE)
        for f in frases:             # sin partir una frase sana por la mitad
            if f["inicio"] < a < f["fin"]:
                a = f["inicio"]
            if f["inicio"] < b < f["fin"]:
                b = min(inicio + largo, f["fin"])
        progreso.aviso(f"Whisper se quedó repitiendo una frase en {formato_tiempo(a)}–{formato_tiempo(b)}; "
                       "lo repito en tramos más cortos")
        if b - a > 0.8 * largo:      # casi todo el tramo: en dos mitades
            mitad = largo / 2
            frases = (_tramo(video, inicio, mitad, servicio, tmp, progreso)
                      + _tramo(video, inicio + mitad, largo - mitad, servicio, tmp, progreso))
        else:                        # solo la parte dañada; lo de afuera se conserva
            fuera = [f for f in frases if f["fin"] <= a or f["inicio"] >= b]
            frases = sorted(fuera + _tramo(video, a, b - a, servicio, tmp, progreso), key=lambda f: f["inicio"])
    elif malas:
        frases = _sin_repeticiones(frases, malas)
    return [f for f in frases if not INVENTADAS.search(f["texto"])]


def transcribir(carpeta: Path, progreso: Progreso | None = None) -> Path:
    """carpeta/video.mp4 → carpeta/transcripcion.json con frases y sus tiempos.
    Los tiempos son los del video analizado (ya recortado), igual que fotogramas.csv."""
    progreso = progreso or Progreso()
    servicio = config.cargar().transcripcion()
    if servicio is None:
        raise FaltaLlave("Falta una clave de transcripción (Whisper). Agrégala en Ajustes.")
    modelo = servicio[2]
    video = carpeta / "video.mp4"
    total = duracion(video)
    frases = []
    with tempfile.TemporaryDirectory() as tmp:
        inicio = 0.0
        while inicio < total:
            largo = min(TRAMO_AUDIO, total - inicio)
            progreso.aviso(f"Transcribiendo {formato_tiempo(inicio)}–{formato_tiempo(inicio + largo)}",
                           inicio / total)
            frases += _tramo(video, inicio, largo, servicio, Path(tmp), progreso)
            inicio += TRAMO_AUDIO
    destino = carpeta / "transcripcion.json"
    destino.write_text(json.dumps({"modelo": modelo, "frases": frases}, ensure_ascii=False, indent=1) + "\n")
    return destino


# ---------------------------------------------------------------- lecturas
INSTRUCCIONES = """Eres un asistente que marca, en la transcripción de un sermón en español, \
las frases en que el predicador LEE EN VOZ ALTA el texto de la Biblia (cualquier versión: \
NBLA, RVR1960, NVI, LBLA, etc.).

Cuenta como lectura: el texto bíblico dicho tal cual o casi tal cual, aunque Whisper lo haya \
transcrito con errores, aunque sea un solo versículo o una cita de otro libro.
NO cuenta: el anuncio («abramos en Romanos 11», «leamos el versículo 5»), la explicación, la \
paráfrasis con palabras propias, los comentarios intercalados entre versículos, las oraciones \
ni las alusiones sueltas a una frase bíblica dentro de la predicación.
Si una frase mezcla lectura y comentario, márcala si la mayor parte es lectura.

Marca también, aparte, las ORACIONES: las frases en que el predicador ESTÁ ORANDO en ese \
momento, hablándole a Dios con la congregación («Señor, te pedimos…», «Padre, gracias…»), desde \
que empieza a hablarle a Dios hasta el «amén». Lo normal es una al empezar y otra al terminar \
el sermón; en medio de la predicación casi nunca hay.
NO es oración: invitar a orar («oremos», «acompáñenme a orar»), hablar de la oración, contar o \
citar lo que alguien oró («y yo decía: Señor, tú gobiernas…»), proponer qué decirle a Dios \
(«digamos: Señor…»), las exclamaciones sueltas («gloria a Dios», «bendito sea el Señor») ni \
explicar el texto aunque nombre a Dios muchas veces. Ante la duda, no la marques: una oración \
mal marcada deja ese tramo fuera de la medición.

Responde SOLO con JSON:
{"lecturas": [{"ids": [números de frase], "referencia": "Ro 11:33-36"}],
 "oraciones": [{"ids": [números de frase]}]}
Agrupa en un mismo elemento las frases seguidas. Listas vacías si no hay. Si no reconoces la \
referencia, déjala en ""."""


SALIDA_GROQ = 16000          # tokens de respuesta (razonamiento incluido) que se le piden a Groq
OPCIONALES = ("temperature", "max_completion_tokens")   # si el modelo rechaza uno, se quita


def consultar_json(url, llave, modelo, instrucciones, texto, progreso=None) -> dict:
    """Una consulta a un modelo de lenguaje (API compatible con OpenAI) que responde JSON."""
    cuerpo = {"model": modelo, "temperature": 0,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": instrucciones},
                           {"role": "user", "content": texto}]}
    if url == config.GROQ_URL:
        # Si no se le pide más, Groq corta la respuesta en unos 3000 tokens, y el razonamiento
        # del modelo cuenta: el JSON llegaba cortado o vacío (HTTP 400 «json_validate_failed»).
        cuerpo["max_completion_tokens"] = SALIDA_GROQ
    while True:
        try:
            r = _pedir(f"{url}/chat/completions", llave, json.dumps(cuerpo).encode(), "application/json", progreso)
            break
        except RuntimeError as e:
            # Hay modelos que rechazan un parámetro (los de razonamiento de OpenAI no aceptan
            # fijar la temperatura): se repite la consulta sin él.
            rechazado = next((p for p in OPCIONALES if p in cuerpo and p in str(e)), None)
            if rechazado is None and "max_completion_tokens" in cuerpo and "HTTP 413" in str(e):
                # «Petición demasiado grande»: por si lo pedido cuenta contra el límite por minuto.
                rechazado = "max_completion_tokens"
            if isinstance(e, FaltaLlave) or rechazado is None:
                raise
            del cuerpo[rechazado]
    contenido = r["choices"][0]["message"]["content"] or "{}"
    contenido = contenido.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError:
        raise RuntimeError(f"El modelo {modelo} no respondió JSON válido.") from None
    return datos if isinstance(datos, dict) else {}


def _consultar(url, llave, modelo, texto, progreso=None) -> dict:
    return consultar_json(url, llave, modelo, INSTRUCCIONES, texto, progreso)


def marcar_lecturas(carpeta: Path, progreso: Progreso | None = None, unir: float = 3.0) -> Path:
    """transcripcion.json → lecturas.json: tramos [inicio, fin] de lectura bíblica y de
    oración. Une tramos separados por menos de `unir` segundos."""
    progreso = progreso or Progreso()
    frases = json.loads((carpeta / "transcripcion.json").read_text())["frases"]
    modelo_cfg = config.cargar().modelo_lecturas()
    if modelo_cfg is None:
        raise FaltaLlave("Falta configurar el modelo para marcar lecturas. Revísalo en Ajustes.")
    url, llave, modelo = modelo_cfg
    marcadas: dict[int, str] = {}
    oraciones: set[int] = set()
    if frases:
        fin_total = frases[-1]["fin"]
        a = 0.0
        while a < fin_total:
            b = a + TRAMO_TEXTO
            ids = [i for i, f in enumerate(frases) if f["inicio"] < b and f["fin"] > a - SOLAPE]
            if ids:
                progreso.aviso(f"Buscando lecturas {formato_tiempo(a)}–{formato_tiempo(min(b, fin_total))}",
                               a / fin_total)
                texto = "\n".join(f"[{i}] ({formato_tiempo(frases[i]['inicio'])}) {frases[i]['texto']}" for i in ids)
                r = _consultar(url, llave, modelo, texto, progreso)
                for lectura in r.get("lecturas", []):
                    for i in lectura.get("ids", []):
                        if isinstance(i, int) and 0 <= i < len(frases):
                            marcadas.setdefault(i, lectura.get("referencia") or "")
                for oracion in r.get("oraciones", []):
                    oraciones.update(i for i in oracion.get("ids", [])
                                     if isinstance(i, int) and 0 <= i < len(frases))
            a = b

    tramos, orar = _unir_lecturas(frases, marcadas, unir), _unir_oraciones(frases, oraciones - set(marcadas), unir)
    destino = carpeta / "lecturas.json"
    destino.write_text(json.dumps({"modelo": modelo, "lecturas": tramos, "oraciones": orar},
                                  ensure_ascii=False, indent=1) + "\n")
    return destino


def _unir_lecturas(frases: list[dict], marcadas: dict[int, str], unir: float) -> list[dict]:
    tramos = []
    for i in sorted(marcadas):
        f = frases[i]
        if tramos and f["inicio"] - tramos[-1]["fin"] <= unir:
            tramos[-1]["fin"] = f["fin"]
            if marcadas[i] and marcadas[i] not in tramos[-1]["referencia"]:
                tramos[-1]["referencia"] = "; ".join(x for x in (tramos[-1]["referencia"], marcadas[i]) if x)
            tramos[-1]["texto"] += " " + f["texto"]
        else:
            tramos.append({"inicio": f["inicio"], "fin": f["fin"], "referencia": marcadas[i], "texto": f["texto"]})
    for t in tramos:
        t["minuto"] = formato_tiempo(t["inicio"])
    return tramos


def _unir_oraciones(frases: list[dict], ids: set[int], unir: float) -> list[dict]:
    orar = []
    for i in sorted(ids):
        f = frases[i]
        if orar and f["inicio"] - orar[-1]["fin"] <= unir:
            orar[-1]["fin"] = f["fin"]
            orar[-1]["texto"] += " " + f["texto"]
        else:
            orar.append({"inicio": f["inicio"], "fin": f["fin"], "texto": f["texto"]})
    for t in orar:
        t["minuto"] = formato_tiempo(t["inicio"])
    return orar


def leer_lecturas(carpeta: Path, clave: str = "lecturas") -> list[tuple[float, float]]:
    ruta = carpeta / "lecturas.json"
    if not ruta.exists():
        return []
    return [(float(t["inicio"]), float(t["fin"])) for t in json.loads(ruta.read_text()).get(clave, [])]
