import json
import os
import stat
from pathlib import Path

import pytest

from mirame import biblioteca, config, lecturas, rutas
from mirame.video import es_url, formato_tiempo, leer_tiempo


@pytest.mark.parametrize("texto, seg", [("90", 90), ("1:30", 90), ("1:02:03", 3723), (None, None)])
def test_leer_tiempo(texto, seg):
    assert leer_tiempo(texto) == seg


def test_formato_tiempo():
    assert formato_tiempo(59.6) == "1:00"
    assert formato_tiempo(3723) == "1:02:03"


def test_es_url():
    assert es_url("https://youtu.be/abc")
    assert es_url("youtube.com/watch?v=abc")
    assert not es_url("/videos/sermon.mp4")


# ---------------------------------------------------------------- configuración
def test_sin_claves_no_separa_lecturas():
    c = config.cargar()
    assert not c.puede_transcribir and not c.puede_separar_lecturas
    assert c.modelo_lecturas() is None


def test_guardar_claves_con_permisos_privados():
    c = config.guardar({"groq_clave": "gsk_1234567890abcdef"})
    assert c.puede_separar_lecturas
    assert c.modelo_lecturas() == (config.GROQ_URL, "gsk_1234567890abcdef", config.LLM_POR_DEFECTO)
    ruta = rutas.configuracion()
    if os.name == "posix":
        assert stat.S_IMODE(ruta.stat().st_mode) == 0o600
    pub = c.publica()
    assert "1234567890" not in pub["groq_clave"]


def test_clave_enmascarada_no_reemplaza_la_guardada():
    config.guardar({"groq_clave": "gsk_1234567890abcdef"})
    c = config.guardar({"groq_clave": "gsk_…cdef"})
    assert c.groq_clave == "gsk_1234567890abcdef"


def test_otro_proveedor_requiere_url_clave_y_modelo():
    c = config.guardar({"groq_clave": "g" * 20, "llm_url": "https://x/v1/", "llm_clave": "k"})
    assert c.modelo_lecturas() is None
    c = config.guardar({"llm_modelo": "m"})
    assert c.modelo_lecturas() == ("https://x/v1", "k", "m")


def test_el_entorno_tiene_prioridad(monkeypatch):
    config.guardar({"groq_clave": "del-archivo-123456"})
    monkeypatch.setenv("GROQ_API_KEY", "del-entorno-123456")
    c = config.cargar()
    assert c.groq_clave == "del-entorno-123456"
    assert "groq_clave" in c.publica()["desde_entorno"]


def test_con_solo_openai_transcribe_y_analiza():
    c = config.guardar({"openai_clave": "sk-1234567890abcdef"})
    assert c.transcripcion() == (config.OPENAI_URL, "sk-1234567890abcdef", config.WHISPER_OPENAI)
    assert c.modelo_lecturas() == (config.OPENAI_URL, "sk-1234567890abcdef", config.LLM_OPENAI)
    assert c.modelo_estructura() == (config.OPENAI_URL, "sk-1234567890abcdef", config.LLM_OPENAI_ESTRUCTURA)
    assert c.puede_separar_lecturas and c.puede_analizar_estructura
    assert "1234567890" not in c.publica()["openai_clave"]


def test_con_groq_y_openai_cada_uno_hace_lo_suyo():
    c = config.guardar({"groq_clave": "gsk_1234567890abcdef", "openai_clave": "sk-1234567890abcdef"})
    assert c.transcripcion()[0] == config.GROQ_URL          # Whisper: Groq
    assert c.modelo_estructura()[0] == config.OPENAI_URL    # texto: OpenAI
    c = config.guardar({"openai_modelo": "gpt-x"})
    assert c.modelo_lecturas()[2] == c.modelo_estructura()[2] == "gpt-x"
    c = config.guardar({"llm_url": "https://x/v1", "llm_clave": "k", "llm_modelo": "m"})
    assert c.modelo_estructura() == ("https://x/v1", "k", "m")   # el proveedor propio manda


def test_solo_groq_tambien_analiza_la_estructura():
    c = config.guardar({"groq_clave": "gsk_1234567890abcdef"})
    assert c.modelo_estructura() == (config.GROQ_URL, "gsk_1234567890abcdef", config.LLM_POR_DEFECTO)


def test_api_elige_quien_hace_todo(monkeypatch):
    """Con las dos claves, `api` manda: "openai" o "groq" hacen todo; vacío es lo automático."""
    c = config.guardar({"groq_clave": "gsk_1234567890abcdef", "openai_clave": "sk-1234567890abcdef", "api": "OpenAI"})
    assert c.api == "openai"
    assert c.transcripcion() == (config.OPENAI_URL, "sk-1234567890abcdef", config.WHISPER_OPENAI)
    assert c.modelo_lecturas()[0] == c.modelo_estructura()[0] == config.OPENAI_URL
    c = config.guardar({"api": "groq"})
    assert c.transcripcion()[0] == config.GROQ_URL
    assert c.modelo_lecturas() == c.modelo_estructura() == (config.GROQ_URL, "gsk_1234567890abcdef", config.LLM_POR_DEFECTO)
    assert c.publica()["en_uso"]["estructura"] == f"Groq · {config.LLM_POR_DEFECTO}"
    assert "1234567890" not in json.dumps(c.publica())

    # Gana también al proveedor propio, y no toma su modelo.
    c = config.guardar({"llm_url": "https://x/v1", "llm_clave": "k", "llm_modelo": "m"})
    assert c.modelo_estructura() == (config.GROQ_URL, "gsk_1234567890abcdef", config.LLM_POR_DEFECTO)
    c = config.guardar({"api": ""})
    assert c.modelo_estructura() == ("https://x/v1", "k", "m")
    assert c.transcripcion()[0] == config.GROQ_URL

    # Un valor desconocido es lo automático; el entorno tiene prioridad.
    assert config.guardar({"api": "otra"}).api == ""
    monkeypatch.setenv("MIRAME_API", "openai")
    assert config.cargar().transcripcion()[0] == config.OPENAI_URL


def test_servicio_propio_de_whisper_con_openai_y_api():
    """En lo automático manda el servicio de Whisper propio; `api` gana y no toma su modelo;
    sin Groq ni servicio propio, la clave de OpenAI también transcribe."""
    c = config.guardar({"groq_clave": "gsk_1234567890abcdef", "openai_clave": "sk-1234567890abcdef",
                        "whisper_url": "https://w/v1/", "whisper_clave": "k", "whisper_modelo": "w"})
    assert c.transcripcion() == ("https://w/v1", "k", "w")
    assert c.modelo_lecturas()[0] == config.OPENAI_URL
    assert "whisper_clave" in config.SECRETOS and "openai_clave" in config.SECRETOS
    c = config.guardar({"api": "groq"})
    assert c.transcripcion() == (config.GROQ_URL, "gsk_1234567890abcdef", config.WHISPER_POR_DEFECTO)
    assert config.guardar({"api": "openai"}).transcripcion() == (config.OPENAI_URL, "sk-1234567890abcdef", config.WHISPER_OPENAI)
    c = config.guardar({"api": "", "whisper_url": "", "whisper_clave": "", "whisper_modelo": "", "groq_clave": ""})
    assert c.transcripcion() == (config.OPENAI_URL, "sk-1234567890abcdef", config.WHISPER_OPENAI)
    assert c.puede_separar_lecturas and c.puede_analizar_estructura


def test_api_sin_su_clave_no_usa_otra():
    c = config.guardar({"groq_clave": "gsk_1234567890abcdef", "api": "openai"})
    assert c.transcripcion() is None and c.modelo_estructura() is None
    assert not c.puede_separar_lecturas and not c.puede_analizar_estructura
    assert c.publica()["en_uso"] == {"transcripcion": "", "lecturas": "", "estructura": ""}


# ---------------------------------------------------------------- transcripción
def test_whisper_en_bucle_y_frases_inventadas():
    amara = {"texto": "Subtítulos realizados por la comunidad de Amara.org"}
    assert lecturas._en_bucle([amara] * 30 + [{"texto": "Buenas noches, hermanos."}])
    assert not lecturas._en_bucle([{"texto": f"frase {i}"} for i in range(30)] + [{"texto": "Amén."}] * 4)
    assert not lecturas._en_bucle([amara] * 3)
    # El bucle puede ir dentro de las frases, partido entre varias y sin que ninguna se repita igual.
    frases = [{"texto": t} for t in (
        "Dios gobierna la historia", "la historia de la humanidad y la", "humanidad, y la humanidad, y la humanidad, y la",
        "humanidad y la", "humanidad", "Tú tienes el control, Señor")]
    assert lecturas._bucles(frases) == {1, 2, 3, 4}
    # Una repetición retórica no es un bucle.
    assert not lecturas._en_bucle([{"texto": t} for t in (
        "santo, santo, santo es el Señor", "no temas, no temas, no temas, no temas",
        "gloria a Dios, gloria a Dios, gloria a Dios")])
    limpias = lecturas._sin_repeticiones(frases, {1, 2, 3, 4})
    assert [f["texto"] for f in limpias] == ["Dios gobierna la historia", "la historia de la humanidad y la",
                                            "humanidad", "Tú tienes el control, Señor"]
    assert lecturas.INVENTADAS.search(amara["texto"])
    assert lecturas.INVENTADAS.search("Buenos días, señoras y señores diputados.")
    assert not lecturas.INVENTADAS.search("Abramos la Biblia en Esdras 5.")


def test_tramo_en_bucle_se_repite_en_mitades(tmp_path, monkeypatch):
    """Si Whisper repite una frase en casi todo el tramo, se vuelve a pedir partido en dos."""
    pedidos = []

    def falso_pedir(url, llave, cuerpo, tipo, progreso=None):
        inicio, largo = pedidos[-1]
        if largo > 100:     # tramos largos: bucle de punta a punta; cortos: texto real
            return {"segments": [{"start": i * 20, "end": i * 20 + 19, "text": "Subtítulos por la comunidad de Amara.org"}
                                 for i in range(10)], "words": []}
        return {"segments": [{"start": 1.0, "end": 3.0, "text": f"texto desde {inicio:.0f}"}], "words": []}

    def falso_ffmpeg(cmd, check):
        pedidos.append((float(cmd[cmd.index("-ss") + 1]), float(cmd[cmd.index("-t") + 1])))
        Path(cmd[-1]).write_bytes(b"mp3")

    monkeypatch.setattr(lecturas, "_pedir", falso_pedir)
    monkeypatch.setattr(lecturas.subprocess, "run", falso_ffmpeg)
    frases = lecturas._tramo(tmp_path / "video.mp4", 0.0, 200.0, ("u", "k", "m"), tmp_path, lecturas.Progreso())
    assert pedidos == [(0.0, 200.0), (0.0, 100.0), (100.0, 100.0)]
    assert [f["texto"] for f in frases] == ["texto desde 0", "texto desde 100"]
    assert [f["inicio"] for f in frases] == [1.0, 101.0]


def test_bucle_en_medio_del_tramo_solo_repite_esa_parte(tmp_path, monkeypatch):
    """Un bucle de dos minutos dentro de un tramo de veinte: se vuelve a pedir solo esa parte
    y lo que estaba bien se conserva."""
    pedidos = []

    def falso_pedir(url, llave, cuerpo, tipo, progreso=None):
        inicio, largo = pedidos[-1]
        if largo == 1200:
            bucle = [{"start": 30.0 + 20 * i, "end": 45.0 + 20 * i, "text": "y la humanidad, y la humanidad, y la humanidad"}
                     for i in range(6)]
            return {"words": [], "segments": [{"start": 20.0, "end": 26.0, "text": "Dios gobierna la historia"}, *bucle,
                                              {"start": 148.0, "end": 156.0, "text": "Tú tienes el control, Señor"},
                                              {"start": 600.0, "end": 606.0, "text": "y el segundo punto"}]}
        return {"words": [], "segments": [{"start": 2.0, "end": 8.0, "text": "Quiero empezar con una pregunta"}]}

    def falso_ffmpeg(cmd, check):
        pedidos.append((float(cmd[cmd.index("-ss") + 1]), float(cmd[cmd.index("-t") + 1])))
        Path(cmd[-1]).write_bytes(b"mp3")

    monkeypatch.setattr(lecturas, "_pedir", falso_pedir)
    monkeypatch.setattr(lecturas.subprocess, "run", falso_ffmpeg)
    frases = lecturas._tramo(tmp_path / "video.mp4", 0.0, 1200.0, ("u", "k", "m"), tmp_path, lecturas.Progreso())
    # El bucle va de 0:30 a 2:25; con el margen se repite desde la frase sana anterior (0:20) hasta la siguiente (2:36).
    assert pedidos == [(0.0, 1200.0), (20.0, 136.0)]
    assert [(f["inicio"], f["texto"]) for f in frases] == [
        (22.0, "Quiero empezar con una pregunta"), (600.0, "y el segundo punto")]


def test_partir_frases_largas_por_palabra():
    seg = [{"start": 0.0, "end": 20.0, "text": "Así todo Israel será salvo. Esto describe un misterio"}]
    palabras = [{"start": i * 0.5, "end": i * 0.5 + 0.4, "word": w} for i, w in
                enumerate(["Así", "todo", "Israel", "será", "salvo."])]
    palabras += [{"start": 10 + i * 0.5, "end": 10.4 + i * 0.5, "word": w} for i, w in
                 enumerate(["Esto", "describe", "un", "misterio"])]
    frases = lecturas._partir(seg, palabras, desfase=100)
    assert [f["texto"] for f in frases] == ["Así todo Israel será salvo.", "Esto describe un misterio"]
    assert frases[0]["inicio"] == 100.0 and frases[1]["inicio"] == 110.0


def test_unir_lecturas_cercanas():
    frases = [{"inicio": 0, "fin": 4, "texto": "a"}, {"inicio": 5, "fin": 9, "texto": "b"},
              {"inicio": 30, "fin": 33, "texto": "c"}]
    tramos = lecturas._unir_lecturas(frases, {0: "Ro 11:25", 1: "Ro 11:26", 2: ""}, unir=3)
    assert [(t["inicio"], t["fin"]) for t in tramos] == [(0, 9), (30, 33)]
    assert tramos[0]["referencia"] == "Ro 11:25; Ro 11:26"


def test_transcribir_sin_clave_avisa(tmp_path):
    with pytest.raises(lecturas.FaltaLlave):
        lecturas.transcribir(tmp_path)


# ---------------------------------------------------------------- biblioteca
def _analisis_falso(nombre, pct=60.0):
    c = rutas.analisis() / nombre
    c.mkdir()
    (c / "resumen.json").write_text(json.dumps({
        "video": {"titulo": f"Sermón {nombre}", "duracion_analizada": 60},
        "pct_congregacion": pct, "pct_abajo": 100 - pct}))
    return c


def test_listar_y_borrar():
    _analisis_falso("2026-01-01_a")
    _analisis_falso("2026-02-01_b", 70)
    fichas = biblioteca.listar()
    assert [f["id"] for f in fichas] == ["2026-02-01_b", "2026-01-01_a"]
    assert fichas[0]["pct_congregacion"] == 70 and fichas[0]["estado"] == "listo"
    biblioteca.borrar("2026-01-01_a")
    assert [f["id"] for f in biblioteca.listar()] == ["2026-02-01_b"]


@pytest.mark.parametrize("malo", ["..", "../x", "a/b", "", ".oculto", "x" * 200])
def test_carpeta_de_rechaza_rutas_raras(malo):
    with pytest.raises(biblioteca.NoExiste):
        biblioteca.carpeta_de(malo)


def test_analisis_sin_resumen_es_incompleto():
    (rutas.analisis() / "2026-03-01_c").mkdir()
    assert biblioteca.listar()[0]["estado"] == "incompleto"


# ---------------------------------------------------------------- 0.4.0
def test_whisper_de_otro_proveedor():
    from mirame import config
    c = config.guardar({"whisper_url": "https://api.openai.com/v1/", "whisper_clave": "sk-x", "whisper_modelo": "whisper-1"})
    assert c.transcripcion() == ("https://api.openai.com/v1", "sk-x", "whisper-1")
    assert c.puede_transcribir and not c.puede_separar_lecturas      # falta el modelo de análisis
    c = config.guardar({"llm_url": "https://x/v1", "llm_clave": "k", "llm_modelo": "m"})
    assert c.puede_separar_lecturas


def test_advertencias_antes_de_procesar():
    from mirame import proceso
    assert any("dura 1:32:00" in a for a in proceso.advertencias(92 * 60, None, None))
    assert proceso.advertencias(92 * 60, 10 * 60, 50 * 60) == []
    assert any("menos de 5 minutos" in a for a in proceso.advertencias(3600, 60, 180))


def test_estimacion_crece_con_el_video_y_las_lecturas():
    from mirame import proceso
    corto, largo = proceso.estimar(600), proceso.estimar(3600)
    assert 0 < corto["segundos"] < largo["segundos"]
    assert proceso.estimar(3600, lecturas=True)["segundos"] > largo["segundos"]


def test_avance_general_pondera_las_etapas():
    from mirame.progreso import Progreso

    class Mudo(Progreso):
        def _mostrar(self, texto):
            pass

    p = Mudo()
    p.plan = ["Obteniendo el video", "Recortando el sermón", "Midiendo la mirada"]
    p.etapa_nueva("Obteniendo el video")
    p.etapa_nueva("Recortando el sermón")
    p.etapa_nueva("Midiendo la mirada")
    p.fraccion = 0.5
    assert 0.55 < p.general() < 0.65      # 20 de 85 hechos + la mitad de 65
