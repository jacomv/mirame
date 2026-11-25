"""Los análisis guardados: listarlos, abrir uno y borrarlo."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from . import rutas

ID_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


class NoExiste(LookupError):
    pass


def carpeta_de(id_: str) -> Path:
    """Carpeta de un análisis por su id (el nombre de la carpeta). Rechaza rutas raras."""
    if not ID_VALIDO.match(id_ or "") or ".." in id_:
        raise NoExiste(id_)
    carpeta = rutas.analisis() / id_
    if not carpeta.is_dir():
        raise NoExiste(id_)
    return carpeta


def _leer(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _fecha_carpeta(carpeta: Path) -> str:
    if re.match(r"^\d{4}-\d{2}-\d{2}", carpeta.name):
        return carpeta.name[:10]
    return datetime.fromtimestamp(carpeta.stat().st_mtime).date().isoformat()


def ficha(carpeta: Path) -> dict:
    """Lo que la biblioteca muestra de un análisis."""
    resumen = _leer(carpeta / "resumen.json")
    estado = _leer(carpeta / "estado.json")
    v = resumen.get("video", {})
    b = resumen.get("biblia") or {}
    c = resumen.get("contacto") or {}
    if resumen:
        situacion = estado.get("estado", "listo")
    else:
        situacion = estado.get("estado") or "incompleto"
        if situacion == "listo":
            situacion = "incompleto"
    tam = sum(f.stat().st_size for f in carpeta.rglob("*") if f.is_file())
    return {
        "id": carpeta.name,
        "titulo": v.get("titulo") or estado.get("titulo") or carpeta.name,
        "origen": v.get("origen") or estado.get("origen"),
        "creado": estado.get("creado") or _fecha_carpeta(carpeta),
        "estado": situacion,
        "duracion": v.get("duracion_analizada"),
        "inicio": v.get("inicio"),
        "pct_congregacion": resumen.get("pct_congregacion"),
        "pct_notas": b.get("pct_abajo_fuera_de_biblia", resumen.get("pct_abajo")),
        "pct_biblia": b.get("pct_abajo_leyendo_biblia"),
        "mirada_media": c.get("duracion_media"),
        "con_lecturas": bool(resumen.get("biblia")) or (carpeta / "lecturas.json").exists(),
        "con_estructura": (carpeta / "estructura.json").exists(),
        "tiene_reporte": (carpeta / "reporte.html").exists(),
        "megabytes": round(tam / 1e6, 1),
    }


def listar() -> list[dict]:
    fichas = [ficha(c) for c in rutas.analisis().iterdir()
              if c.is_dir() and not c.name.startswith(".") and ID_VALIDO.match(c.name)]
    return sorted(fichas, key=lambda f: (f["creado"] or "", f["id"]), reverse=True)


def borrar(id_: str) -> None:
    """Borra la carpeta del análisis. La descarga original del video queda en caché."""
    carpeta = carpeta_de(id_)
    if carpeta.parent.resolve() != rutas.analisis().resolve():
        raise NoExiste(id_)
    shutil.rmtree(carpeta)


def cache_descargas() -> dict:
    """Videos completos descargados de YouTube. Se reutilizan si se vuelve a analizar el
    mismo enlace; se pueden borrar sin afectar los análisis (cada uno tiene su recorte)."""
    archivos = [f for f in rutas.descargas().iterdir() if f.is_file()]
    return {"archivos": len(archivos), "megabytes": round(sum(f.stat().st_size for f in archivos) / 1e6, 1)}


def vaciar_descargas() -> int:
    n = 0
    for f in rutas.descargas().iterdir():
        if f.is_file():
            f.unlink()
            n += 1
    return n
