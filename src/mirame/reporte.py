"""Reporte HTML autocontenido: el video del sermón con los datos sincronizados.

La plantilla está en assets/reporte/ (HTML, CSS y JS por separado); aquí se une todo
en un solo archivo con los datos del análisis incrustados."""

from __future__ import annotations

import json
import math
from importlib import resources
from pathlib import Path

import pandas as pd

from . import estructura
from .analisis import leer_fotogramas, leer_resumen

CLASES = ["congregacion", "abajo", "sin_dato", "excluido"]


def _n(v, d=2):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(float(v), d)


def _lecturas(carpeta: Path) -> list:
    ruta = carpeta / "lecturas.json"
    if not ruta.exists():
        return []
    return [[t["inicio"], t["fin"], t.get("referencia") or ""] for t in json.loads(ruta.read_text())["lecturas"]]


def _estructura(carpeta: Path, titulo: str) -> tuple[dict | None, str | None]:
    """La estructura del sermón y su versión en texto (para el botón Copiar). Si el
    archivo se editó a mano y quedó incompleto, el reporte se genera sin ella."""
    datos = estructura.leer(carpeta)
    if datos is None:
        return None, None
    try:
        return datos, estructura.texto(datos, titulo)
    except (KeyError, TypeError):
        return None, None


def generar(carpeta: Path) -> Path:
    carpeta = carpeta.resolve()
    resumen = leer_resumen(carpeta)
    fot = leer_fotogramas(carpeta)
    seg = pd.read_csv(carpeta / "segundos.csv")
    idx = {c: i for i, c in enumerate(CLASES)}

    titulo_video = resumen["video"].get("titulo") or carpeta.name
    sermon, sermon_texto = _estructura(carpeta, titulo_video)
    datos = {
        "titulo": titulo_video,
        "carpeta": str(carpeta),
        "duracion": resumen["video"]["duracion_analizada"],
        "ancho": resumen["video"].get("ancho", 1280),
        "alto": resumen["video"].get("alto", 720),
        "resumen": resumen,
        "segundos": [[int(r.t), idx[r.clase], _n(r.pitch, 1)] for r in seg.itertuples()],
        "lecturas": _lecturas(carpeta),
        "estructura": sermon,
        "estructura_texto": sermon_texto,
        "fotogramas": [
            [idx[r.clase], _n(r.pitch, 1)] + ([_n(r.x, 4), _n(r.y, 4), _n(r.w, 4), _n(r.h, 4),
                                               _n(getattr(r, "ojos", None), 2)] if r.rostro else [])
            for r in fot.itertuples()
        ],
    }
    activos = resources.files("mirame") / "assets"
    plantilla = (activos / "reporte" / "plantilla.html").read_text()
    css = (activos / "reporte" / "reporte.css").read_text()
    js = (activos / "reporte" / "reporte.js").read_text()
    chart = (activos / "vendor" / "chart.umd.min.js").read_text()
    titulo = datos["titulo"].replace("&", "&amp;").replace("<", "&lt;")
    # Un solo archivo autocontenido: se abre sin conexión y se puede compartir tal cual.
    html = (plantilla
            .replace("__TITULO__", titulo)
            .replace("/*CSS*/", css)
            .replace("/*CHARTJS*/", chart.replace("</script", "<\\/script"))
            .replace("/*JS*/", js)
            .replace("/*DATOS*/", json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
                     .replace("</", "<\\/")))
    destino = carpeta / "reporte.html"
    destino.write_text(html)
    return destino
