"""Claves y modelos de IA opcionales.

Sin claves, Mírame mide igual la mirada. Con ellas, además transcribe el audio,
separa la lectura bíblica y las oraciones (lo que hace el resultado más preciso) y
analiza la estructura y el contenido del sermón.

Dos pasos, cada uno con su proveedor (cualquier API compatible con OpenAI). Basta una
clave, de Groq o de OpenAI; con `api` vacío se elige solo:
- Transcripción (Whisper): el servicio propio si se configuró; si no, Groq; si no, OpenAI
  con `whisper-1`.
- Análisis de la transcripción (marcar lecturas y analizar la estructura): el proveedor
  propio si se configuró; si no, OpenAI; si no, Groq.

Con `api` en "groq" u "openai" se usa solo esa API para los dos pasos, aunque haya otras
claves o proveedores propios.

Se guardan en `<carpeta de datos>/configuracion.json` con permisos solo para el
usuario (0600). Las variables de entorno tienen prioridad sobre el archivo.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields

from . import rutas

GROQ_URL = "https://api.groq.com/openai/v1"
WHISPER_POR_DEFECTO = "whisper-large-v3-turbo"
LLM_POR_DEFECTO = "openai/gpt-oss-120b"
OPENAI_URL = "https://api.openai.com/v1"
WHISPER_OPENAI = "whisper-1"             # el único de OpenAI que devuelve el tiempo de cada palabra
LLM_OPENAI = "gpt-5.4"                   # marcar lecturas: rápido; el «mini» confunde predicación con oración
LLM_OPENAI_ESTRUCTURA = "gpt-5.5"        # estructura del sermón: razona sobre el sermón completo
APIS = ("groq", "openai")                # valores de `api`; cualquier otro = automático

# campo → variable de entorno que lo reemplaza
ENTORNO = {
    "groq_clave": "GROQ_API_KEY",
    "whisper_url": "MIRAME_WHISPER_URL",
    "whisper_clave": "MIRAME_WHISPER_KEY",
    "whisper_modelo": "MIRAME_WHISPER_MODELO",
    "llm_url": "MIRAME_LLM_URL",
    "llm_clave": "MIRAME_LLM_KEY",
    "llm_modelo": "MIRAME_LLM_MODELO",
    "openai_clave": "OPENAI_API_KEY",
    "openai_modelo": "MIRAME_OPENAI_MODELO",
    "api": "MIRAME_API",
}
SECRETOS = ("groq_clave", "whisper_clave", "llm_clave", "openai_clave")


@dataclass
class Configuracion:
    groq_clave: str = ""        # transcripción (Whisper) y, si no hay otro, el modelo de lecturas
    whisper_url: str = ""       # otro servicio de Whisper compatible con OpenAI; vacío = Groq
    whisper_clave: str = ""
    whisper_modelo: str = ""    # vacío = whisper-large-v3-turbo (Groq)
    llm_url: str = ""           # API compatible con OpenAI para marcar lecturas; vacío = Groq
    llm_clave: str = ""
    llm_modelo: str = ""        # vacío = openai/gpt-oss-120b en Groq
    openai_clave: str = ""      # transcripción (whisper-1) y modelo de lenguaje con OpenAI
    openai_modelo: str = ""     # vacío = gpt-5.4 para lecturas y gpt-5.5 para la estructura
    api: str = ""               # "groq" u "openai": usar solo esa API; vacío = automático

    # ---- valores efectivos
    @property
    def api_elegida(self) -> str:
        """"groq", "openai" o "" (automático)."""
        v = self.api.strip().lower()
        return v if v in APIS else ""

    def transcripcion(self) -> tuple[str, str, str] | None:
        """(url, clave, modelo) para transcribir, o None si no hay con qué."""
        # `whisper_modelo` es del servicio propio cuando hay `whisper_url`; si no, es el de Groq.
        en_groq = (self.whisper_modelo if not self.whisper_url else "") or WHISPER_POR_DEFECTO
        groq = (GROQ_URL, self.groq_clave, en_groq) if self.groq_clave else None
        openai = (OPENAI_URL, self.openai_clave, WHISPER_OPENAI) if self.openai_clave else None
        if self.api_elegida:
            return groq if self.api_elegida == "groq" else openai
        if self.whisper_url:
            if not self.whisper_clave or not self.whisper_modelo:
                return None
            return self.whisper_url.rstrip("/"), self.whisper_clave, self.whisper_modelo
        return groq or openai

    def _modelo(self, de_openai: str) -> tuple[str, str, str] | None:
        # `llm_modelo` es del proveedor propio cuando hay `llm_url`; si no, es el de Groq.
        en_groq = (self.llm_modelo if not self.llm_url else "") or LLM_POR_DEFECTO
        groq = (GROQ_URL, self.groq_clave, en_groq) if self.groq_clave else None
        openai = (OPENAI_URL, self.openai_clave, self.openai_modelo or de_openai) if self.openai_clave else None
        if self.api_elegida:
            return groq if self.api_elegida == "groq" else openai
        if self.llm_url:
            if not self.llm_clave or not self.llm_modelo:
                return None
            return self.llm_url.rstrip("/"), self.llm_clave, self.llm_modelo
        return openai or groq

    def modelo_lecturas(self) -> tuple[str, str, str] | None:
        """(url, clave, modelo) para marcar lecturas, o None si no hay con qué."""
        return self._modelo(LLM_OPENAI)

    def modelo_estructura(self) -> tuple[str, str, str] | None:
        """(url, clave, modelo) para analizar la estructura del sermón."""
        return self._modelo(LLM_OPENAI_ESTRUCTURA)

    @property
    def puede_transcribir(self) -> bool:
        return self.transcripcion() is not None

    @property
    def puede_separar_lecturas(self) -> bool:
        return self.puede_transcribir and self.modelo_lecturas() is not None

    @property
    def puede_analizar_estructura(self) -> bool:
        return self.puede_transcribir and self.modelo_estructura() is not None

    def publica(self) -> dict:
        """Para mostrar en la interfaz: las claves enmascaradas."""
        d = asdict(self)
        for k in SECRETOS:
            d[k] = _enmascarar(d[k])
        d["api"] = self.api_elegida
        d["desde_entorno"] = [k for k, v in ENTORNO.items() if os.environ.get(v)]
        d["en_uso"] = {paso: _nombre(servicio) for paso, servicio in (
            ("transcripcion", self.transcripcion()), ("lecturas", self.modelo_lecturas()),
            ("estructura", self.modelo_estructura()))}
        d["puede_transcribir"] = self.puede_transcribir
        d["puede_separar_lecturas"] = self.puede_separar_lecturas
        d["puede_analizar_estructura"] = self.puede_analizar_estructura
        return d


def _nombre(servicio: tuple[str, str, str] | None) -> str:
    """«OpenAI · gpt-5.5»: quién hace cada paso, para mostrarlo en Ajustes. Sin la clave."""
    if servicio is None:
        return ""
    url, _, modelo = servicio
    quien = {GROQ_URL: "Groq", OPENAI_URL: "OpenAI"}.get(url) or url.split("//")[-1].split("/")[0]
    return f"{quien} · {modelo}"


def _enmascarar(v: str) -> str:
    if not v:
        return ""
    return v[:4] + "…" + v[-4:] if len(v) > 12 else "…"


def _archivo() -> dict:
    ruta = rutas.configuracion()
    if not ruta.exists():
        return {}
    try:
        return json.loads(ruta.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def cargar() -> Configuracion:
    datos = _archivo()
    valores = {}
    for f in fields(Configuracion):
        valores[f.name] = os.environ.get(ENTORNO[f.name], "").strip() or str(datos.get(f.name, "")).strip()
    return Configuracion(**valores)


def guardar(cambios: dict) -> Configuracion:
    """Actualiza solo los campos recibidos. Una clave enmascarada («abcd…wxyz») se
    ignora: significa que el usuario no la cambió."""
    datos = _archivo()
    for f in fields(Configuracion):
        if f.name not in cambios:
            continue
        v = str(cambios[f.name] or "").strip()
        if f.name in SECRETOS and "…" in v:
            continue
        if f.name == "api":
            v = v.lower() if v.lower() in APIS else ""
        datos[f.name] = v
    ruta = rutas.configuracion()
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(ruta)
    return cargar()
