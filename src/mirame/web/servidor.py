"""Servidor local de la app: páginas, API JSON y archivos de cada análisis.

Solo escucha en 127.0.0.1: nada queda expuesto a la red. Usa solo la biblioteca
estándar (http.server) para no sumar dependencias.

Rutas
-----
GET    /                                 la app (static/index.html)
GET    /static/<archivo>                 CSS y JS de la app
GET    /api/estado                       versión, carpeta de datos, ajustes y capacidades
GET    /api/analisis                     biblioteca
DELETE /api/analisis/<id>                borrar un análisis
POST   /api/analisis/<id>/lecturas       separar lectura bíblica y oración
POST   /api/analisis/<id>/estructura     analizar la estructura y el contenido del sermón
POST   /api/analizar                     nuevo análisis {origen, inicio, fin, titulo, ...}
POST   /api/subir?nombre=<archivo>       subir un video local (cuerpo = bytes del archivo)
POST   /api/info                         título, duración y miniatura de un enlace {origen}
POST   /api/estimar                      tiempo estimado y advertencias {duracion, inicio, fin, ...}
GET    /api/trabajos                     trabajos en curso y recientes
POST   /api/trabajos/<n>/cancelar
GET    /api/ajustes   POST /api/ajustes  claves de IA
POST   /api/ajustes/probar               comprobar una clave
POST   /api/descargas/vaciar             borrar la caché de videos descargados
GET    /analisis/<id>/<archivo>          reporte, video (con Range) y capturas
POST   /analisis/<id>/capturar?t=&modo=  captura PNG del reporte
"""

from __future__ import annotations

import contextlib
import json
import mimetypes
import re
import threading
import urllib.request
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .. import __version__, biblioteca, capturar, config, lecturas, proceso, rutas, video
from ..video import es_url, leer_tiempo
from .trabajos import Cola

ESTATICOS = resources.files("mirame") / "web" / "static"
TAM_BLOQUE = 1 << 20


class ErrorPeticion(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def _tiempo(texto) -> float | None:
    if texto in (None, ""):
        return None
    try:
        return leer_tiempo(str(texto))
    except ValueError:
        raise ErrorPeticion(400, f"Tiempo no válido: «{texto}». Usa mm:ss o hh:mm:ss.") from None


class App:
    """Estado compartido entre peticiones."""

    def __init__(self):
        self.cola = Cola()
        self.candado_capturas = threading.Lock()

    # ---- trabajos
    def nuevo_analisis(self, datos: dict) -> dict:
        origen = str(datos.get("origen") or "").strip()
        if not origen:
            raise ErrorPeticion(400, "Pega el enlace de YouTube o elige un archivo de video.")
        if not es_url(origen) and not Path(origen).expanduser().exists():
            raise ErrorPeticion(400, "Eso no parece un enlace de YouTube ni un archivo que exista.")
        inicio, fin = _tiempo(datos.get("inicio")), _tiempo(datos.get("fin"))
        if inicio is not None and fin is not None and fin <= inicio:
            raise ErrorPeticion(400, "El fin del sermón debe ser después del inicio.")
        try:
            fps = float(datos.get("fps") or 4)
            umbral = float(datos.get("umbral") or 15)
            umbral_ojos = float(datos.get("umbral_ojos") or 0.45)
        except ValueError:
            raise ErrorPeticion(400, "Los valores avanzados deben ser números.") from None
        if not 1 <= fps <= 25:
            raise ErrorPeticion(400, "Los fotogramas por segundo deben estar entre 1 y 25.")
        op = proceso.Opciones(
            origen=origen, inicio=inicio, fin=fin, titulo=(datos.get("titulo") or "").strip() or None,
            fps=fps, umbral=umbral, umbral_ojos=None if datos.get("solo_cabeza") else umbral_ojos,
            separar_lecturas=bool(datos.get("separar_lecturas")),
            estructura=bool(datos.get("estructura")),
        )

        def correr(progreso):
            carpeta, _ = proceso.analizar(op, progreso)
            return carpeta.name

        titulo = op.titulo or (origen if es_url(origen) else Path(origen).name)
        return self.cola.agregar("analizar", titulo, correr).publico()

    def separar(self, id_: str) -> dict:
        carpeta = biblioteca.carpeta_de(id_)
        if self.cola.ocupado(id_):
            raise ErrorPeticion(409, "Ese análisis ya tiene un trabajo en curso.")
        if not config.cargar().puede_separar_lecturas:
            raise ErrorPeticion(400, "Primero agrega una clave de IA en Ajustes.")
        titulo = biblioteca.ficha(carpeta)["titulo"]

        def correr(progreso):
            proceso.separar_lecturas(carpeta, progreso)
            return id_

        return self.cola.agregar("lecturas", titulo, correr, analisis=id_).publico()

    def estructura(self, id_: str) -> dict:
        carpeta = biblioteca.carpeta_de(id_)
        if self.cola.ocupado(id_):
            raise ErrorPeticion(409, "Ese análisis ya tiene un trabajo en curso.")
        if not config.cargar().puede_analizar_estructura:
            raise ErrorPeticion(400, "Primero agrega una clave de IA en Ajustes.")
        if not (carpeta / "resumen.json").exists():
            raise ErrorPeticion(400, "Ese análisis no terminó: vuelve a analizarlo.")
        titulo = biblioteca.ficha(carpeta)["titulo"]

        def correr(progreso):
            proceso.analizar_estructura(carpeta, progreso)
            return id_

        return self.cola.agregar("estructura", titulo, correr, analisis=id_).publico()

    def borrar(self, id_: str) -> None:
        biblioteca.carpeta_de(id_)
        if self.cola.ocupado(id_):
            raise ErrorPeticion(409, "No se puede borrar mientras tiene un trabajo en curso.")
        biblioteca.borrar(id_)

    # ---- estado
    def estado(self) -> dict:
        return {
            "version": __version__,
            "datos": str(rutas.datos()),
            "ajustes": config.cargar().publica(),
            "capturas": capturar.disponible(),
            "descargas": biblioteca.cache_descargas(),
        }


def probar_clave(datos: dict) -> dict:
    """Comprueba una clave contra la API. Usa la guardada si la recibida viene enmascarada."""
    guardada = config.cargar()
    tipo = datos.get("tipo")
    if tipo == "whisper":
        url = (datos.get("whisper_url") or "").strip()
        clave = datos.get("whisper_clave") or ""
        clave = guardada.whisper_clave if (not clave or "…" in clave) else clave
        if not url or not clave:
            raise ErrorPeticion(400, "Escribe la URL y la clave del servicio de transcripción.")
    elif tipo == "groq":
        clave = datos.get("groq_clave") or ""
        clave = guardada.groq_clave if (not clave or "…" in clave) else clave
        if not clave:
            raise ErrorPeticion(400, "Escribe la clave de Groq.")
        url = config.GROQ_URL
    elif tipo == "openai":
        clave = datos.get("openai_clave") or ""
        clave = guardada.openai_clave if (not clave or "…" in clave) else clave
        if not clave:
            raise ErrorPeticion(400, "Escribe la clave de OpenAI.")
        url = config.OPENAI_URL
    else:
        url = (datos.get("llm_url") or "").strip()
        clave = datos.get("llm_clave") or ""
        clave = guardada.llm_clave if (not clave or "…" in clave) else clave
        if not url or not clave:
            raise ErrorPeticion(400, "Escribe la URL y la clave del proveedor.")
    try:
        modelos = lecturas.probar(url, clave)
    except lecturas.FaltaLlave as e:
        return {"ok": False, "mensaje": str(e)}
    except RuntimeError as e:
        return {"ok": False, "mensaje": str(e)}
    return {"ok": True, "mensaje": f"Funciona: {len(modelos)} modelos disponibles.", "modelos": modelos[:300]}


def crear_manejador(app: App, puerto: int):
    origenes = {f"http://127.0.0.1:{puerto}", f"http://localhost:{puerto}"}

    class Manejador(BaseHTTPRequestHandler):
        server_version = f"mirame/{__version__}"

        def log_message(self, *args):
            pass

        # ---------------------------------------------------------- utilidades
        def _json(self, cuerpo, codigo: int = 200):
            datos = json.dumps(cuerpo, ensure_ascii=False).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(datos)

        def _cuerpo_json(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n))
            except json.JSONDecodeError:
                raise ErrorPeticion(400, "JSON no válido.") from None

        def _mismo_origen(self):
            # Protege la API de páginas de otros sitios abiertas en el mismo navegador.
            origen = self.headers.get("Origin")
            if origen and origen not in origenes:
                raise ErrorPeticion(403, "Origen no permitido.")
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in ("127.0.0.1", "localhost"):
                raise ErrorPeticion(403, "Host no permitido.")

        def _archivo(self, ruta: Path, cache: bool = False):
            """Sirve un archivo; soporta Range para poder saltar en el video."""
            if not ruta.is_file():
                raise ErrorPeticion(404, "No existe.")
            tam = ruta.stat().st_size
            tipo = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
            if tipo.startswith("text/") or tipo in ("application/javascript", "application/json"):
                tipo += "; charset=utf-8"
            inicio, fin = 0, tam - 1
            rango = self.headers.get("Range")
            m = re.match(r"bytes=(\d*)-(\d*)$", rango or "")
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    inicio = int(m.group(1))
                    fin = min(int(m.group(2)), tam - 1) if m.group(2) else tam - 1
                else:
                    inicio = max(tam - int(m.group(2)), 0)
                if inicio > fin or inicio >= tam:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{tam}")
                    self.end_headers()
                    return
                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self.send_header("Content-Range", f"bytes {inicio}-{fin}/{tam}")
            else:
                self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", tipo)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(fin - inicio + 1))
            self.send_header("Cache-Control", "max-age=3600" if cache else "no-cache")
            self.end_headers()
            if self.command == "HEAD":
                return
            with ruta.open("rb") as f:
                f.seek(inicio)
                quedan = fin - inicio + 1
                try:
                    while quedan > 0:
                        bloque = f.read(min(TAM_BLOQUE, quedan))
                        if not bloque:
                            break
                        self.wfile.write(bloque)
                        quedan -= len(bloque)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # el navegador cortó (p. ej. al saltar en el video)

        def _despachar(self, metodo: str):
            try:
                url = urlparse(self.path)
                partes = [unquote(p) for p in url.path.strip("/").split("/") if p]
                if metodo != "GET":
                    self._mismo_origen()
                self._ruta(metodo, partes, parse_qs(url.query))
            except ErrorPeticion as e:
                self._json({"error": str(e)}, e.codigo)
            except biblioteca.NoExiste:
                self._json({"error": "Ese análisis no existe."}, 404)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:  # noqa: BLE001
                import traceback
                traceback.print_exc()
                self._json({"error": f"Error interno: {e}"}, 500)

        def do_GET(self):
            self._despachar("GET")

        def do_HEAD(self):
            self._despachar("GET")

        def do_POST(self):
            self._despachar("POST")

        def do_DELETE(self):
            self._despachar("DELETE")

        # ---------------------------------------------------------- rutas
        def _ruta(self, metodo: str, p: list[str], q: dict):
            if metodo == "GET" and (not p or p == ["index.html"]):
                return self._archivo(Path(str(ESTATICOS / "index.html")))
            if metodo == "GET" and len(p) == 2 and p[0] == "static":
                if not re.match(r"^[\w.-]+$", p[1]):
                    raise ErrorPeticion(404, "No existe.")
                return self._archivo(Path(str(ESTATICOS / p[1])))
            if p and p[0] == "api":
                return self._api(metodo, p[1:], q)
            if len(p) >= 3 and p[0] == "analisis":
                carpeta = biblioteca.carpeta_de(p[1])
                if metodo == "POST" and p[2:] == ["capturar"]:
                    return self._capturar(carpeta, q)
                if metodo == "GET":
                    destino = (carpeta / "/".join(p[2:])).resolve()
                    if carpeta.resolve() not in destino.parents:
                        raise ErrorPeticion(404, "No existe.")
                    return self._archivo(destino, cache=destino.suffix in (".mp4", ".png", ".jpg"))
            raise ErrorPeticion(404, "No existe.")

        def _api(self, metodo: str, p: list[str], q: dict):
            if metodo == "GET" and p == ["estado"]:
                return self._json(app.estado())
            if metodo == "GET" and p == ["analisis"]:
                return self._json(biblioteca.listar())
            if len(p) == 2 and p[0] == "analisis" and metodo == "DELETE":
                app.borrar(p[1])
                return self._json({"ok": True})
            if len(p) == 3 and p[0] == "analisis" and p[2] == "lecturas" and metodo == "POST":
                return self._json(app.separar(p[1]))
            if len(p) == 3 and p[0] == "analisis" and p[2] == "estructura" and metodo == "POST":
                return self._json(app.estructura(p[1]))
            if p == ["analizar"] and metodo == "POST":
                return self._json(app.nuevo_analisis(self._cuerpo_json()))
            if p == ["info"] and metodo == "POST":
                origen = str(self._cuerpo_json().get("origen") or "").strip()
                if not origen:
                    raise ErrorPeticion(400, "Falta el enlace.")
                try:
                    return self._json(video.info(origen))
                except FileNotFoundError as e:
                    raise ErrorPeticion(400, str(e)) from None
                except Exception as e:  # noqa: BLE001 — yt-dlp: enlace inválido, privado, sin red…
                    raise ErrorPeticion(400, "No pude leer ese video. Revisa el enlace o tu conexión. "
                                             f"({str(e)[:160]})") from None
            if p == ["estimar"] and metodo == "POST":
                d = self._cuerpo_json()
                total = float(d.get("duracion") or 0)
                inicio, fin = _tiempo(d.get("inicio")), _tiempo(d.get("fin"))
                tramo = (fin if fin is not None else total) - (inicio or 0)
                return self._json({
                    **proceso.estimar(max(tramo, 0), float(d.get("fps") or 4), bool(d.get("lecturas")),
                                      bool(d.get("descargar")), bool(d.get("estructura"))),
                    "tramo": tramo,
                    "advertencias": proceso.advertencias(total, inicio, fin),
                })
            if p == ["subir"] and metodo == "POST":
                return self._json(self._subir(q))
            if p == ["trabajos"] and metodo == "GET":
                return self._json(app.cola.lista())
            if len(p) == 3 and p[0] == "trabajos" and p[2] == "cancelar" and metodo == "POST":
                return self._json({"ok": app.cola.cancelar(int(p[1]))})
            if p == ["ajustes"] and metodo == "GET":
                return self._json(config.cargar().publica())
            if p == ["ajustes"] and metodo == "POST":
                return self._json(config.guardar(self._cuerpo_json()).publica())
            if p == ["ajustes", "probar"] and metodo == "POST":
                return self._json(probar_clave(self._cuerpo_json()))
            if p == ["descargas", "vaciar"] and metodo == "POST":
                return self._json({"borrados": biblioteca.vaciar_descargas()})
            raise ErrorPeticion(404, "No existe.")

        def _subir(self, q: dict) -> dict:
            """Guarda un video local subido desde la página en la carpeta de descargas."""
            nombre = Path((q.get("nombre") or ["video.mp4"])[0]).name
            nombre = re.sub(r"[^\w.\- ]+", "_", nombre).strip() or "video.mp4"
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                raise ErrorPeticion(400, "El archivo está vacío.")
            destino = rutas.descargas() / "subidos"
            destino.mkdir(exist_ok=True)
            ruta = destino / nombre
            tmp = ruta.with_suffix(ruta.suffix + ".parcial")
            with tmp.open("wb") as f:
                quedan = n
                while quedan > 0:
                    bloque = self.rfile.read(min(TAM_BLOQUE, quedan))
                    if not bloque:
                        break
                    f.write(bloque)
                    quedan -= len(bloque)
            if quedan:
                tmp.unlink(missing_ok=True)
                raise ErrorPeticion(400, "La subida se cortó.")
            tmp.replace(ruta)
            return {"ruta": str(ruta), "nombre": nombre}

        def _capturar(self, carpeta: Path, q: dict):
            t = float((q.get("t") or ["0"])[0])
            modo = (q.get("modo") or ["momento"])[0]
            if modo not in ("momento", "resumen"):
                raise ErrorPeticion(400, "Modo no válido.")
            try:
                with app.candado_capturas:
                    png = capturar.capturar(carpeta, [(capturar.nombre_en(t, modo), t, modo)])[0]
            except capturar.SinNavegador as e:
                raise ErrorPeticion(501, str(e)) from None
            return self._json({"archivo": str(png), "url": f"/analisis/{carpeta.name}/capturas/{png.name}"})

    return Manejador


def _escuchar(puerto: int, manejador_de) -> ThreadingHTTPServer:
    for intento in range(20):
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", puerto + intento), None)
        except OSError:
            continue
        servidor.RequestHandlerClass = manejador_de(servidor.server_address[1])
        return servidor
    raise SystemExit(f"No encontré un puerto libre entre {puerto} y {puerto + 19}.")


def _ya_abierta(puerto: int) -> bool:
    """¿Hay una Mírame corriendo en ese puerto? (doble clic al acceso directo con la app abierta)."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/estado", timeout=1) as r:
            return "version" in json.load(r)
    except Exception:
        return False


def iniciar(puerto: int = 8710, abrir: bool = True, ruta: str = "/") -> None:
    """Arranca la app y abre el navegador. Ctrl+C para cerrarla."""
    if _ya_abierta(puerto):
        url = f"http://127.0.0.1:{puerto}{ruta}"
        print(f"Mírame ya está abierta en {url}")
        if abrir:
            webbrowser.open(url)
        return
    app = App()
    servidor = _escuchar(puerto, lambda p: crear_manejador(app, p))
    url = f"http://127.0.0.1:{servidor.server_address[1]}{ruta}"
    print(f"Mírame {__version__} en {url}")
    print(f"Datos en {rutas.datos()}")
    print("Para cerrarla, cierra esta ventana o pulsa Ctrl+C.", flush=True)
    if abrir:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrado.")


def servir_carpeta(carpeta: Path, puerto: int = 8710, abrir: bool = True) -> None:
    """Sirve un análisis que está fuera de la biblioteca (p. ej. una copia en otra carpeta)."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler

    candado = threading.Lock()

    class Manejador(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            url = urlparse(self.path)
            if url.path != "/capturar":
                return self.send_error(404)
            q = parse_qs(url.query)
            t, modo = float(q.get("t", ["0"])[0]), q.get("modo", ["momento"])[0]
            try:
                with candado:
                    png = capturar.capturar(carpeta, [(capturar.nombre_en(t, modo), t, modo)])[0]
                cuerpo, codigo = {"archivo": str(png)}, 200
            except Exception as e:  # noqa: BLE001
                cuerpo, codigo = {"error": str(e)}, 500
            datos = json.dumps(cuerpo).encode()
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

    servidor = _escuchar(puerto, lambda p: partial(Manejador, directory=str(carpeta)))
    url = f"http://127.0.0.1:{servidor.server_address[1]}/reporte.html"
    print(f"Reporte en {url}  (Ctrl+C para cerrar)")
    if abrir:
        webbrowser.open(url)
    with contextlib.suppress(KeyboardInterrupt):
        servidor.serve_forever()
