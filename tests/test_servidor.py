"""La API de la app, contra un servidor real en un puerto libre."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from mirame import rutas
from mirame.web import servidor


@pytest.fixture()
def base():
    app = servidor.App()
    srv = servidor._escuchar(18710, lambda p: servidor.crear_manejador(app, p))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def pedir(url, metodo="GET", cuerpo=None, cabeceras=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json", **(cabeceras or {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def test_pagina_y_estado(base):
    codigo, cuerpo, _ = pedir(base + "/")
    assert codigo == 200 and "Mírame".encode() in cuerpo
    codigo, cuerpo, _ = pedir(base + "/api/estado")
    estado = json.loads(cuerpo)
    assert codigo == 200 and estado["ajustes"]["puede_transcribir"] is False


def test_validaciones_al_analizar(base):
    codigo, cuerpo, _ = pedir(base + "/api/analizar", "POST", {"origen": ""})
    assert codigo == 400
    codigo, cuerpo, _ = pedir(base + "/api/analizar", "POST",
                              {"origen": "https://youtu.be/x", "inicio": "10:00", "fin": "5:00"})
    assert codigo == 400 and "después" in json.loads(cuerpo)["error"]


def test_estructura_pide_clave(base):
    (rutas.analisis() / "2026-01-01_x").mkdir()
    codigo, cuerpo, _ = pedir(base + "/api/analisis/2026-01-01_x/estructura", "POST")
    assert codigo == 400 and "clave" in json.loads(cuerpo)["error"]
    codigo, _, _ = pedir(base + "/api/analisis/no-existe/estructura", "POST")
    assert codigo == 404


def test_rechaza_otros_origenes(base):
    codigo, _, _ = pedir(base + "/api/ajustes", "POST", {"groq_clave": "x"},
                         {"Origin": "https://sitio-malicioso.example"})
    assert codigo == 403


def test_guardar_ajustes_enmascara(base):
    codigo, cuerpo, _ = pedir(base + "/api/ajustes", "POST", {"groq_clave": "gsk_1234567890abcdef"})
    assert codigo == 200
    assert json.loads(cuerpo)["groq_clave"] == "gsk_…cdef"


def test_video_con_range(base):
    c = rutas.analisis() / "2026-01-01_x"
    c.mkdir()
    (c / "video.mp4").write_bytes(bytes(range(256)) * 4)
    codigo, cuerpo, cab = pedir(base + "/analisis/2026-01-01_x/video.mp4", cabeceras={"Range": "bytes=10-19"})
    assert codigo == 206 and cuerpo == bytes(range(10, 20))
    assert cab["Content-Range"] == "bytes 10-19/1024"


def test_no_sale_de_la_carpeta(base):
    (rutas.analisis() / "2026-01-01_x").mkdir()
    (rutas.datos() / "secreto.txt").write_text("no")
    codigo, _, _ = pedir(base + "/analisis/2026-01-01_x/..%2F..%2Fsecreto.txt")
    assert codigo == 404


def test_borrar(base):
    (rutas.analisis() / "2026-01-01_x").mkdir()
    codigo, _, _ = pedir(base + "/api/analisis/2026-01-01_x", "DELETE")
    assert codigo == 200 and not (rutas.analisis() / "2026-01-01_x").exists()
    codigo, _, _ = pedir(base + "/api/analisis/2026-01-01_x", "DELETE")
    assert codigo == 404


def test_estimar(base):
    codigo, cuerpo, _ = pedir(base + "/api/estimar", "POST", {"duracion": 5400, "inicio": "", "fin": ""})
    d = json.loads(cuerpo)
    assert codigo == 200 and d["tramo"] == 5400 and d["segundos"] > 0
    assert d["advertencias"]                          # video largo sin recortar
    codigo, cuerpo, _ = pedir(base + "/api/estimar", "POST", {"duracion": 5400, "inicio": "10:00", "fin": "50:00"})
    assert json.loads(cuerpo)["tramo"] == 2400
