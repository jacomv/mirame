"""Cola de trabajos largos (analizar, separar lecturas, estructura del sermón) para la app web.

Corren de uno en uno en un hilo aparte: el análisis usa mucho CPU y dos a la vez solo
tardarían más. La página consulta el estado cada segundo.
"""

from __future__ import annotations

import itertools
import queue
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field

from ..progreso import Cancelado, Progreso


class ProgresoWeb(Progreso):
    """Guarda el estado y las últimas líneas para mostrarlas en la página."""

    def __init__(self):
        super().__init__()
        self.lineas: list[str] = []

    def _mostrar(self, texto: str) -> None:
        print(texto, flush=True)
        self.lineas = (self.lineas + [texto.strip()])[-40:]


@dataclass
class Trabajo:
    id: int
    tipo: str                       # "analizar" | "lecturas" | "estructura"
    titulo: str
    funcion: Callable[[ProgresoWeb], str | None]   # devuelve el id del análisis
    estado: str = "en_cola"         # en_cola | corriendo | listo | error | cancelado
    analisis: str | None = None
    error: str | None = None
    creado: float = field(default_factory=time.time)
    terminado: float | None = None
    progreso: ProgresoWeb = field(default_factory=ProgresoWeb)

    def publico(self) -> dict:
        p = self.progreso
        return {
            "id": self.id, "tipo": self.tipo, "titulo": self.titulo, "estado": self.estado,
            "analisis": self.analisis, "error": self.error,
            "etapa": p.etapa, "fraccion": p.fraccion, "mensaje": p.mensaje, "lineas": p.lineas[-8:],
            "plan": p.plan, "hechas": p.hechas,
            "general": 1.0 if self.estado == "listo" else round(p.general(), 3),
            "restante": None if self.estado != "corriendo" else p.restante(),
            "transcurrido": round((self.terminado or time.time()) - self.creado),
            "creado": self.creado, "terminado": self.terminado,
        }


class Cola:
    def __init__(self):
        self._trabajos: dict[int, Trabajo] = {}
        self._cola: queue.Queue[Trabajo] = queue.Queue()
        self._ids = itertools.count(1)
        self._candado = threading.Lock()
        threading.Thread(target=self._bucle, daemon=True, name="mirame-trabajos").start()

    def agregar(self, tipo: str, titulo: str, funcion, analisis: str | None = None) -> Trabajo:
        with self._candado:
            t = Trabajo(id=next(self._ids), tipo=tipo, titulo=titulo, funcion=funcion, analisis=analisis)
            self._trabajos[t.id] = t
        self._cola.put(t)
        return t

    def obtener(self, id_: int) -> Trabajo | None:
        return self._trabajos.get(id_)

    def lista(self) -> list[dict]:
        # Los terminados se muestran 10 minutos; después basta con la biblioteca.
        limite = time.time() - 600
        return [t.publico() for t in sorted(self._trabajos.values(), key=lambda t: t.id, reverse=True)
                if t.terminado is None or t.terminado > limite]

    def ocupado(self, id_analisis: str) -> bool:
        return any(t.analisis == id_analisis and t.estado in ("en_cola", "corriendo")
                   for t in self._trabajos.values())

    def cancelar(self, id_: int) -> bool:
        t = self._trabajos.get(id_)
        if not t or t.estado not in ("en_cola", "corriendo"):
            return False
        t.progreso.cancelar()
        if t.estado == "en_cola":
            t.estado, t.terminado = "cancelado", time.time()
        return True

    def _bucle(self):
        while True:
            t = self._cola.get()
            if t.estado != "en_cola":
                continue
            t.estado = "corriendo"
            try:
                resultado = t.funcion(t.progreso)
                t.analisis = resultado or t.analisis
                t.estado = "listo"
            except Cancelado:
                t.estado = "cancelado"
            except Exception as e:  # noqa: BLE001 — se muestra en la página
                if t.progreso.cancelado:  # p. ej. yt-dlp envuelve la cancelación en su propio error
                    t.estado = "cancelado"
                else:
                    traceback.print_exc()
                    t.estado, t.error = "error", _mensaje(e)
            finally:
                t.terminado = time.time()


def _mensaje(e: Exception) -> str:
    texto = str(e) or e.__class__.__name__
    if "Sign in to confirm" in texto or "bot" in texto.lower():
        return ("YouTube pidió verificar que no eres un robot. Prueba más tarde, actualiza yt-dlp "
                "o descarga el video y súbelo como archivo.")
    if "Video unavailable" in texto or "Private video" in texto:
        return "YouTube dice que el video no está disponible (privado, borrado o con restricción)."
    return texto[:500]
