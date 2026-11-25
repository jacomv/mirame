"""mirame — ¿hacia dónde mira el predicador?

Sin argumentos abre la app en el navegador. Los subcomandos hacen lo mismo desde la terminal.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# MediaPipe/TensorFlow Lite escriben mucho en stderr; solo errores.
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

from . import __version__  # noqa: E402
from .video import formato_tiempo, leer_tiempo  # noqa: E402


def _rango(texto: str) -> tuple[float, float]:
    a, b = texto.split("-", 1)
    return leer_tiempo(a), leer_tiempo(b)


def _carpeta(texto: str) -> Path:
    """Acepta una ruta a la carpeta del análisis o su id en la biblioteca."""
    from . import biblioteca

    ruta = Path(texto).expanduser()
    if ruta.is_dir():
        return ruta.resolve()
    try:
        return biblioteca.carpeta_de(texto)
    except biblioteca.NoExiste:
        sys.exit(f"No encuentro el análisis «{texto}». Usa `mirame lista` para ver los guardados.")


# ---------------------------------------------------------------- app
def cmd_app(a):
    from .web.servidor import iniciar

    iniciar(puerto=a.puerto, abrir=not a.no_abrir)


# ---------------------------------------------------------------- analizar
def cmd_analizar(a):
    from . import analisis, proceso

    op = proceso.Opciones(
        origen=a.origen, inicio=leer_tiempo(a.inicio), fin=leer_tiempo(a.fin), titulo=a.titulo,
        fps=a.fps, umbral=a.umbral, base=a.base,
        calibrar=_rango(a.calibrar) if a.calibrar else None,
        excluir=[_rango(x) for x in a.excluir], ancho_minimo=a.ancho_minimo,
        umbral_ojos=None if a.solo_cabeza else a.umbral_ojos,
        separar_lecturas=False if a.sin_lecturas else None,
        estructura=False if a.sin_estructura else None,
        salida=Path(a.salida) if a.salida else None,
    )
    t0 = time.time()
    try:
        carpeta, resumen = proceso.analizar(op)
    except FileNotFoundError as e:
        sys.exit(str(e))
    print(f"\nListo en {formato_tiempo(time.time() - t0)} → {carpeta}")
    print(analisis.texto_resumen(resumen))
    print(f"\nReporte: {carpeta / 'reporte.html'}")


# ---------------------------------------------------------------- lecturas
def cmd_lecturas(a):
    """Transcribe el audio, marca la lectura bíblica y la oración, y recalcula."""
    import json

    from . import analisis, lecturas, proceso

    carpeta = _carpeta(a.carpeta)
    try:
        resumen = proceso.separar_lecturas(carpeta, retranscribir=a.retranscribir,
                                           solo_recalcular=a.solo_recalcular)
    except lecturas.FaltaLlave as e:
        sys.exit(f"{e}\nConfigúrala con `mirame app` (Ajustes) o con variables de entorno (ver README).")
    datos = json.loads((carpeta / "lecturas.json").read_text())
    print(f"\n{len(datos['lecturas'])} tramos de lectura bíblica ({datos['modelo']}):")
    for t in datos["lecturas"]:
        print(f"  {formato_tiempo(t['inicio'])}–{formato_tiempo(t['fin'])}  {t['referencia'] or '?'}  "
              f"{t['texto'][:70]}…")
    if datos.get("oraciones"):
        print(f"{len(datos['oraciones'])} oraciones:")
        for t in datos["oraciones"]:
            print(f"  {formato_tiempo(t['inicio'])}–{formato_tiempo(t['fin'])}  {t['texto'][:70]}…")
    print()
    print(analisis.texto_resumen(resumen))


# ---------------------------------------------------------------- estructura
def cmd_estructura(a):
    """Transcribe el audio (si hace falta) y analiza la estructura y el contenido del sermón."""
    from . import estructura, lecturas, proceso

    carpeta = _carpeta(a.carpeta)
    if a.mostrar:
        datos = estructura.leer(carpeta)
        if datos is None:
            sys.exit("Ese análisis todavía no tiene estructura. Córrelo sin --mostrar.")
    else:
        try:
            datos = proceso.analizar_estructura(carpeta, retranscribir=a.retranscribir)
        except lecturas.FaltaLlave as e:
            sys.exit(f"{e}\nConfigúrala con `mirame app` (Ajustes) o con variables de entorno (ver README).")
        except (FileNotFoundError, RuntimeError) as e:
            sys.exit(str(e))
        print()
    print(estructura.texto(datos, estructura._titulo(carpeta)))
    print(f"\nGuardado en {carpeta / 'estructura.md'} · se ve en la pestaña «Sermón» del reporte.")


# ---------------------------------------------------------------- recalcular
def cmd_recalcular(a):
    """Reclasifica desde fotogramas.csv con otro umbral o calibración, sin tocar el video."""
    from . import analisis, proceso

    cambios = {}
    if a.umbral is not None:
        cambios["umbral"] = a.umbral
    if a.base is not None:
        cambios["base"] = a.base
    if a.calibrar:
        cambios.update(calibrar=_rango(a.calibrar), base=None)
    if a.excluir:
        cambios["excluir"] = [_rango(x) for x in a.excluir]
    if a.ancho_minimo is not None:
        cambios["ancho_minimo"] = a.ancho_minimo
    if a.umbral_ojos is not None:
        cambios["umbral_ojos"] = a.umbral_ojos
    if a.solo_cabeza:
        cambios["umbral_ojos"] = None
    print(analisis.texto_resumen(proceso.recalcular(_carpeta(a.carpeta), cambios)))


# ---------------------------------------------------------------- lista / borrar
def cmd_lista(a):
    from . import biblioteca, rutas

    fichas = biblioteca.listar()
    print(f"{len(fichas)} análisis en {rutas.analisis()}\n")
    for f in fichas:
        pct = f"{f['pct_congregacion']:5.1f} %" if f["pct_congregacion"] is not None else "   —   "
        print(f"  {f['id']:<36} {pct}  {f['estado']:<11} {f['titulo'][:60]}")


def cmd_borrar(a):
    from . import biblioteca

    carpeta = _carpeta(a.id)
    f = biblioteca.ficha(carpeta)
    if not a.si:
        r = input(f"¿Borrar «{f['titulo']}» ({f['megabytes']} MB)? [s/N] ").strip().lower()
        if r not in ("s", "si", "sí", "y", "yes"):
            sys.exit("No se borró nada.")
    biblioteca.borrar(carpeta.name)
    print(f"Borrado: {carpeta}")


# ---------------------------------------------------------------- muestras
def cmd_muestras(a):
    from . import muestras

    destino = muestras.generar(_carpeta(a.carpeta), n=a.n)
    print(f"Muestras en {destino}")
    for f in sorted(destino.glob("*.jpg")):
        print(f"  {f}")


# ---------------------------------------------------------------- reporte
def cmd_reporte(a):
    import webbrowser

    from . import reporte

    html = reporte.generar(_carpeta(a.carpeta))
    print(html)
    if a.abrir:
        webbrowser.open(html.as_uri())


# ---------------------------------------------------------------- capturar
def cmd_capturar(a):
    from . import capturar

    carpeta = _carpeta(a.carpeta)
    if a.en or a.resumen:
        momentos = [(capturar.nombre_en(leer_tiempo(t)), leer_tiempo(t), "momento") for t in a.en]
        if a.resumen:
            momentos.append(("resumen", 0.0, "resumen"))
    else:
        momentos = capturar.momentos_por_defecto(carpeta)
    t0 = time.time()
    try:
        for png in capturar.capturar(carpeta, momentos):
            print(png)
    except capturar.SinNavegador as e:
        sys.exit(str(e))
    print(f"({time.time() - t0:.1f} s)")


def cmd_instalar_capturas(a):
    """Descarga el Chromium de Playwright que corresponde a la versión instalada."""
    import subprocess

    from . import capturar

    if not capturar.disponible():
        sys.exit(capturar.INSTALAR)
    sys.exit(subprocess.call([sys.executable, "-m", "playwright", "install", "chromium", "--only-shell"]))


def cmd_acceso(a):
    """Acceso directo en el escritorio para abrir la app con doble clic."""
    from .herramientas import crear_acceso

    print(f"Acceso directo creado: {crear_acceso()}")


# ---------------------------------------------------------------- ver
def cmd_ver(a):
    """Abre un reporte dentro de la app (con el botón Capturar activo)."""
    from . import rutas
    from .web.servidor import iniciar, servir_carpeta

    carpeta = _carpeta(a.carpeta)
    if carpeta.parent.resolve() == rutas.analisis().resolve():
        iniciar(puerto=a.puerto, abrir=not a.no_abrir, ruta=f"/analisis/{carpeta.name}/reporte.html")
    else:  # una carpeta fuera de la biblioteca
        servir_carpeta(carpeta, puerto=a.puerto, abrir=not a.no_abrir)


# ---------------------------------------------------------------- validar
def cmd_validar(a):
    """Compara con un etiquetado manual. CSV con `t,clase` (un segundo por fila) o
    `inicio,fin,clase` (rangos). Tiempos en segundos o mm:ss; clase c/a/s o el nombre."""
    import pandas as pd

    nombres = {"c": "congregacion", "a": "abajo", "s": "sin_dato"}
    carpeta = _carpeta(a.carpeta)
    seg = pd.read_csv(carpeta / "segundos.csv").set_index("t")
    manual = pd.read_csv(a.etiquetas, dtype=str)
    manual.columns = [c.strip().lower() for c in manual.columns]
    pares = []
    for r in manual.itertuples():
        v = r.clase.strip().lower().replace("ó", "o")
        clase = nombres.get(v, v)
        if "inicio" in manual.columns:
            segundos = range(int(leer_tiempo(r.inicio)), int(leer_tiempo(r.fin)))
        else:
            segundos = [int(leer_tiempo(r.t))]
        pares += [(s, clase, seg.loc[s, "clase"]) for s in segundos if s in seg.index]
    if not pares:
        sys.exit("Ninguna etiqueta cae dentro del análisis.")
    df = pd.DataFrame(pares, columns=["t", "manual", "mirame"])
    con_dato = df[(df.manual != "sin_dato") & (df.mirame != "sin_dato")]
    print(f"Segundos comparados: {len(df)}")
    print(f"Coincidencia total: {(df.manual == df.mirame).mean() * 100:.1f} %  (objetivo ≥ 90 %)")
    if len(con_dato):
        print(f"Coincidencia donde ambos tienen dato ({len(con_dato)} s): "
              f"{(con_dato.manual == con_dato.mirame).mean() * 100:.1f} %")
    print("\nMatriz (filas = manual, columnas = mirame):")
    print(pd.crosstab(df.manual, df.mirame).to_string())
    errores = df[df.manual != df.mirame]
    if len(errores):
        print("\nPrimeros desacuerdos: " + ", ".join(
            f"{formato_tiempo(r.t)} ({r.manual}→{r.mirame})" for r in errores.head(15).itertuples()))


# ---------------------------------------------------------------- main
def construir() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="mirame", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"mirame {__version__}")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("app", help="abrir la app en el navegador (lo mismo que `mirame` solo)")
    p.add_argument("--puerto", type=int, default=8710)
    p.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    p.set_defaults(fn=cmd_app)

    p = sub.add_parser("analizar", help="analizar un sermón (enlace de YouTube o archivo de video)")
    p.add_argument("origen", help="enlace de YouTube o archivo de video")
    p.add_argument("--inicio", help="mm:ss donde empieza el sermón")
    p.add_argument("--fin", help="mm:ss donde termina")
    p.add_argument("--titulo", help="título para el reporte")
    p.add_argument("--fps", type=float, default=4.0, help="fotogramas por segundo (4)")
    p.add_argument("--umbral", type=float, default=15.0, help="grados sobre la calibración para 'abajo' (15)")
    p.add_argument("--base", type=float, help="inclinación de 'mirando a la congregación' fijada a mano")
    p.add_argument("--calibrar", metavar="mm:ss-mm:ss", help="calibrar con este tramo en vez de todo el sermón")
    p.add_argument("--excluir", action="append", default=[], metavar="mm:ss-mm:ss",
                   help="tramo excluido del cálculo; se puede repetir")
    p.add_argument("--ancho-minimo", type=int, default=0, help="rostros más angostos (px) cuentan como sin dato")
    p.add_argument("--umbral-ojos", type=float, default=0.45,
                   help="puntaje de ojos bajados (0–1) que cuenta como 'abajo' (0.45)")
    p.add_argument("--solo-cabeza", action="store_true", help="ignorar los ojos")
    p.add_argument("--sin-lecturas", action="store_true",
                   help="no separar lectura bíblica ni oración aunque haya claves de IA")
    p.add_argument("--sin-estructura", action="store_true",
                   help="no analizar la estructura del sermón aunque haya claves de IA")
    p.add_argument("--salida", help="carpeta de salida (por defecto, una nueva en la biblioteca)")
    p.set_defaults(fn=cmd_analizar)

    p = sub.add_parser("lecturas", help="transcribir y separar lectura bíblica y oración (requiere clave de IA)")
    p.add_argument("carpeta", help="id del análisis o ruta de su carpeta")
    p.add_argument("--retranscribir", action="store_true", help="volver a transcribir aunque exista")
    p.add_argument("--solo-recalcular", action="store_true",
                   help="no consultar a la IA: aplicar lecturas.json tal como está (p. ej. editado a mano)")
    p.set_defaults(fn=cmd_lecturas)

    p = sub.add_parser("estructura", help="estructura, argumento, evangelio, aplicaciones y pasajes del sermón "
                                          "(requiere clave de IA)")
    p.add_argument("carpeta", help="id del análisis o ruta de su carpeta")
    p.add_argument("--retranscribir", action="store_true", help="volver a transcribir aunque exista")
    p.add_argument("--mostrar", action="store_true", help="solo mostrar el análisis ya guardado, sin consultar a la IA")
    p.set_defaults(fn=cmd_estructura)

    p = sub.add_parser("recalcular", help="reclasificar con otros parámetros, sin volver a procesar el video")
    p.add_argument("carpeta")
    p.add_argument("--umbral", type=float)
    p.add_argument("--base", type=float)
    p.add_argument("--calibrar", metavar="mm:ss-mm:ss")
    p.add_argument("--excluir", action="append", metavar="mm:ss-mm:ss")
    p.add_argument("--ancho-minimo", type=int)
    p.add_argument("--umbral-ojos", type=float)
    p.add_argument("--solo-cabeza", action="store_true")
    p.set_defaults(fn=cmd_recalcular)

    p = sub.add_parser("lista", help="análisis guardados")
    p.set_defaults(fn=cmd_lista)

    p = sub.add_parser("borrar", help="borrar un análisis guardado")
    p.add_argument("id")
    p.add_argument("--si", action="store_true", help="no pedir confirmación")
    p.set_defaults(fn=cmd_borrar)

    p = sub.add_parser("reporte", help="regenerar reporte.html")
    p.add_argument("carpeta")
    p.add_argument("--abrir", action="store_true", help="abrirlo en el navegador")
    p.set_defaults(fn=cmd_reporte)

    p = sub.add_parser("ver", help="abrir un reporte con el botón Capturar activo")
    p.add_argument("carpeta")
    p.add_argument("--puerto", type=int, default=8710)
    p.add_argument("--no-abrir", action="store_true")
    p.set_defaults(fn=cmd_ver)

    p = sub.add_parser("capturar", help="imágenes PNG 1920×1080 del reporte")
    p.add_argument("carpeta")
    p.add_argument("--en", action="append", default=[], metavar="mm:ss", help="momento a capturar; se puede repetir")
    p.add_argument("--resumen", action="store_true", help="capturar la vista de resumen")
    p.set_defaults(fn=cmd_capturar)

    p = sub.add_parser("instalar-capturas", help="descargar el navegador que usan las capturas (una vez)")
    p.set_defaults(fn=cmd_instalar_capturas)

    p = sub.add_parser("acceso", help="crear un acceso directo en el escritorio para abrir la app")
    p.set_defaults(fn=cmd_acceso)

    p = sub.add_parser("muestras", help="fotogramas al azar de cada clase, para revisar a ojo")
    p.add_argument("carpeta")
    p.add_argument("-n", type=int, default=20)
    p.set_defaults(fn=cmd_muestras)

    p = sub.add_parser("validar", help="comparar con un etiquetado manual")
    p.add_argument("carpeta")
    p.add_argument("etiquetas", help="CSV con t,clase o inicio,fin,clase")
    p.set_defaults(fn=cmd_validar)
    return ap


def main(argv=None):
    ap = construir()
    a = ap.parse_args(argv)
    if a.cmd is None:
        a = ap.parse_args(["app"])
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
