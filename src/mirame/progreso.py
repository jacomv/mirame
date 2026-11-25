"""Avance de una tarea larga: lo mismo para la terminal que para la app web."""

from __future__ import annotations

import threading
import time


class Cancelado(Exception):
    """El usuario detuvo la tarea."""


# Peso aproximado de cada etapa en el tiempo total (para la barra de avance general).
PESOS = {
    "Obteniendo el video": 12,
    "Recortando el sermón": 8,
    "Midiendo la mirada": 65,
    "Transcribiendo el audio": 10,
    "Marcando lectura bíblica y oración": 5,
    "Analizando la estructura del sermón": 15,
}


class Progreso:
    """Por defecto imprime en la terminal. La app web usa una subclase que guarda el
    estado para mostrarlo en la página."""

    def __init__(self):
        self._cancelar = threading.Event()
        self.etapa = ""
        self.fraccion: float | None = None
        self.mensaje = ""
        self.carpeta = None   # carpeta del análisis, en cuanto se conoce
        self.plan: list[str] = []       # etapas previstas, en orden
        self.hechas: list[str] = []
        self.inicio = time.time()

    def etapa_nueva(self, nombre: str) -> None:
        if self.etapa and self.etapa not in self.hechas:
            self.hechas.append(self.etapa)
        if nombre not in self.plan:
            self.plan.append(nombre)
        self.etapa, self.fraccion, self.mensaje = nombre, None, ""
        self._mostrar(nombre)

    def general(self) -> float:
        """Avance de toda la tarea (0–1), ponderando cada etapa por su peso típico."""
        total = sum(PESOS.get(e, 5) for e in self.plan) or 1
        hecho = sum(PESOS.get(e, 5) for e in self.hechas)
        if self.etapa and self.etapa not in self.hechas:
            hecho += PESOS.get(self.etapa, 5) * (self.fraccion or 0)
        return min(hecho / total, 1.0)

    def restante(self) -> float | None:
        """Segundos que faltan para terminar todo, cuando ya hay base para estimarlo."""
        g = self.general()
        if g < 0.05:
            return None
        return (time.time() - self.inicio) / g * (1 - g)

    def aviso(self, mensaje: str, fraccion: float | None = None) -> None:
        self.mensaje, self.fraccion = mensaje, fraccion
        self._mostrar(f"  {mensaje}")
        self.revisar()

    def _mostrar(self, texto: str) -> None:
        print(texto, flush=True)

    # ---- cancelación
    def cancelar(self) -> None:
        self._cancelar.set()

    @property
    def cancelado(self) -> bool:
        return self._cancelar.is_set()

    def revisar(self) -> None:
        if self._cancelar.is_set():
            raise Cancelado()


class Cronometro:
    """Estimación de tiempo restante para bucles largos."""

    def __init__(self):
        self.t0 = time.time()

    def restante(self, hecho: float) -> float:
        if hecho <= 0:
            return 0.0
        return (time.time() - self.t0) / hecho * (1 - hecho)
