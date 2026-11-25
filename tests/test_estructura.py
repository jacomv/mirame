"""Estructura del sermón: de las respuestas del modelo a estructura.json, el texto y el reporte."""

import json

import numpy as np
import pandas as pd
import pytest

from mirame import analisis, config, estructura, lecturas, reporte
from mirame.analisis import Parametros

# 60 frases de 10 s: la frase i empieza en el segundo 10·i.
FRASES = [{"inicio": 10.0 * i, "fin": 10.0 * i + 9, "texto": f"frase {i}"} for i in range(60)]

ESTRUCTURA = {
    "tema": "Dios sostiene su obra", "pasaje_principal": "Esdras 5:1-17", "resumen": "Un resumen.",
    "estructura": {"clara": True, "explicacion": "Sigue el texto.", "anuncia_puntos": "sí",
                   "como_los_anuncia": "«lo primero que vemos»",
                   "anuncios": [{"desde": 36, "cita": "«tres razones»", "anuncia": "Escucha", "es_punto": False},
                                {"desde": 10, "cita": "lo primero que vemos [10]", "anuncia": "Dios envía su palabra", "es_punto": True},
                                {"desde": 999, "cita": "apunta a una frase que no existe", "es_punto": True},
                                {"desde": 12}]},
    "introduccion": {"hay": True, "desde": 1, "como_introduce": "Abre con una pregunta.", "acorde": False,
                     "explicacion": "Habla de otra cosa."},
    "partes": [
        {"tipo": "punto", "titulo": "Dios permanece fiel", "anunciado": True, "desde": 30,
         "transicion": "“punto dos, Dios permanece fiel” [30]", "resumen": "R2",
         "subpuntos": [{"titulo": "Escucha", "desde": 35}, {"titulo": "Fuera de la parte", "desde": 5},
                       {"titulo": "", "desde": 36}]},
        {"tipo": "Introducción", "titulo": "", "anunciado": False, "desde": "[0]", "transicion": "", "resumen": "R0"},
        {"tipo": "punto", "titulo": "Dios envía su palabra", "anunciado": True, "desde": 10, "transicion": "", "resumen": "R1"},
        {"tipo": "conclusion", "titulo": "Retomar la obra", "desde": 50},
        {"tipo": "punto", "titulo": "Apunta a una frase que no existe", "desde": 999},
        {"tipo": "invento", "titulo": "Repite el inicio de otra", "desde": 10},
    ],
    "argumento": {"hay": True, "tesis": "No temas.", "valoracion": "Avanza bien.",
                  "desarrollo": [{"desde": 40, "paso": "Segundo"}, {"desde": 12, "paso": "Primero"},
                                 {"desde": None, "paso": "Sin momento"}]},
    "climax": {"hay": True, "desde": 52, "hasta": 54, "descripcion": "Todo lleva ahí.", "cita": "«Cristo venció»"},
}
EVANGELIO = {
    "evangelio": {"presente": True, "resumen": "Lleva el templo a Cristo.",
                  "menciones": [{"aspecto": "Resurrección", "desde": 53, "como": "Venció la muerte", "cita": "c"},
                                {"aspecto": "muerte", "desde": 45, "como": "La cruz", "cita": ""},
                                {"aspecto": "vida", "desde": 46}]},
    "aplicaciones": [{"desde": 55, "aplicacion": "Retoma la obra", "dirigida_a": "creyentes",
                      "se_apoya_en": "Esdras 5:2", "cita": "«levántate»"},
                     {"desde": 20, "aplicacion": ""}],
}
PASAJES = [
    {"pasajes": [{"desde": 2, "referencia": "Esdras 5:1-2", "tipo": "mencionado", "nota": ""},
                 {"desde": 3, "referencia": "Esdras 5:1–2", "tipo": "leído", "nota": "lo lee"},
                 {"desde": 47, "referencia": "Juan 16:33", "tipo": "citado", "nota": "paz"}]},
    {"pasajes": [{"desde": 47, "referencia": "Juan 16:33", "tipo": "citado"},      # repetida por el solape
                 {"desde": 20, "referencia": "Esdras 5:1-2", "tipo": "raro"},      # misma cita, mucho después
                 {"desde": 21, "referencia": "", "tipo": "citado"},
                 "basura"]},
]


def normalizado():
    return estructura.normalizar(ESTRUCTURA, EVANGELIO, PASAJES, FRASES)


def test_partes_ordenadas_con_su_tiempo_y_numeradas():
    partes = normalizado()["partes"]
    assert [(p["tipo"], p["numero"], p["inicio"], p["fin"]) for p in partes] == [
        ("introduccion", None, 0.0, 100.0), ("punto", 1, 100.0, 300.0),
        ("punto", 2, 300.0, 500.0), ("conclusion", None, 500.0, 599.0)]
    assert [p["minuto"] for p in partes] == ["0:00", "1:40", "5:00", "8:20"]
    assert partes[0]["titulo"] == "Introducción"                       # sin título: el nombre de la parte
    assert partes[2]["transicion"] == "punto dos, Dios permanece fiel"  # sin comillas ni ids de frase
    assert partes[2]["subpuntos"] == [{"inicio": 350.0, "minuto": "5:50", "titulo": "Escucha"}]
    assert partes[3]["anunciado"] is False and partes[3]["resumen"] == ""


def test_argumento_climax_evangelio_y_aplicaciones():
    e = normalizado()
    assert e["estructura"] == {"clara": True, "explicacion": "Sigue el texto.", "anuncia_puntos": True,
                               "como_los_anuncia": "lo primero que vemos", "anuncios": [
        {"inicio": 100.0, "minuto": "1:40", "cita": "lo primero que vemos", "anuncia": "Dios envía su palabra", "es_punto": True},
        {"inicio": 360.0, "minuto": "6:00", "cita": "tres razones", "anuncia": "Escucha", "es_punto": False}]}
    assert [(x["minuto"], x["paso"]) for x in e["argumento"]["desarrollo"]] == [("2:00", "Primero"), ("6:40", "Segundo")]
    assert e["climax"]["inicio"] == 520.0 and e["climax"]["fin"] == 549.0 and e["climax"]["cita"] == "Cristo venció"
    assert [(m["aspecto"], m["inicio"]) for m in e["evangelio"]["menciones"]] == [("muerte", 450.0), ("resurrección", 530.0)]
    assert e["evangelio"]["presente"] is True
    assert [a["aplicacion"] for a in e["aplicaciones"]] == ["Retoma la obra"]


def test_enumerar_dentro_de_un_punto_no_es_anunciar_los_puntos():
    """Las señales van con su minuto, y el veredicto sale de ellas: si lo único que enumeró es
    una lista dentro de un punto, no anunció los puntos del sermón aunque el modelo diga que sí."""
    e = normalizado()
    t = estructura.texto(e)
    assert "  - 1:40 · «lo primero que vemos» → Dios envía su palabra\n" in t
    assert "  - 6:00 · «tres razones» → Escucha *(lista dentro de un punto)*" in t

    solo_lista = {"estructura": {"anuncia_puntos": True, "como_los_anuncia": "Enumera tres tácticas.", "anuncios": [
        {"desde": 40, "cita": "número dos, desanimar", "anuncia": "Desanimar", "es_punto": False}]}}
    forma = estructura.normalizar(solo_lista, {}, [], FRASES)["estructura"]
    assert forma["anuncia_puntos"] is False and [a["minuto"] for a in forma["anuncios"]] == ["6:40"]

    sin_senales = estructura.normalizar({"estructura": {"anuncia_puntos": True}}, {}, [], FRASES)["estructura"]
    assert sin_senales["anuncia_puntos"] is True and sin_senales["anuncios"] == []   # se respeta el veredicto del modelo

    viejo = {**e, "estructura": {k: v for k, v in e["estructura"].items() if k != "anuncios"}}   # un estructura.json anterior
    assert "- **¿Anunció sus puntos?** Sí. lo primero que vemos" in estructura.texto(viejo)


def test_introduccion_y_si_va_acorde_con_el_argumento():
    e = normalizado()
    assert e["introduccion"] == {"hay": True, "inicio": 10.0, "minuto": "0:10", "como_introduce": "Abre con una pregunta.",
                                 "acorde": False, "explicacion": "Habla de otra cosa."}
    assert ("- **¿La introducción va acorde con el argumento?** No. (0:10) Abre con una pregunta. Habla de otra cosa."
            in estructura.texto(e))
    sin = estructura.normalizar({"introduccion": {"hay": False, "acorde": True, "explicacion": "Entra directo al texto."}},
                                {}, [], FRASES)
    assert sin["introduccion"]["hay"] is False and sin["introduccion"]["acorde"] is False
    assert "- **Introducción:** no tiene. Entra directo al texto." in estructura.texto(sin)
    viejo = {k: v for k, v in e.items() if k != "introduccion"}      # un estructura.json anterior a esta pregunta
    assert "introducción" not in estructura.texto(viejo).lower().split("## estructura")[1].split("- **0:00**")[0]


def test_pasajes_sin_repetidos():
    pasajes = normalizado()["pasajes"]
    assert [(p["minuto"], p["referencia"], p["tipo"]) for p in pasajes] == [
        ("0:20", "Esdras 5:1-2", "leido"),        # mencionado + leído seguidos: una cita, la más literal
        ("3:20", "Esdras 5:1-2", "mencionado"),   # vuelve al pasaje más tarde: otra cita
        ("7:50", "Juan 16:33", "citado")]
    assert pasajes[0]["nota"] == "lo lee"


def test_respuestas_vacias_o_rotas_no_rompen():
    e = estructura.normalizar({"partes": "no", "climax": {"hay": True, "desde": "x"}}, None, [None, {}], FRASES)
    assert e["partes"] == [] and e["pasajes"] == [] and e["aplicaciones"] == []
    assert e["climax"]["hay"] is True and e["climax"]["inicio"] is None
    assert e["evangelio"]["presente"] is False
    assert "No se reconocieron" not in estructura.texto(e)   # el texto se arma igual


def test_texto_en_markdown():
    t = estructura.texto(normalizado(), "Cuando Dios pelea conmigo")
    assert t.startswith("# Cuando Dios pelea conmigo")
    assert "- **1:40** · Punto 1: Dios envía su palabra *(anunciado)*" in t
    assert "  - Transición: «punto dos, Dios permanece fiel»" in t
    assert "- **¿Anunció sus puntos?** Sí." in t
    assert "- **8:50** · Resurrección: Venció la muerte «c»" in t
    assert "- **0:20** · Esdras 5:1-2 (leído): lo lee" in t


def test_tramos_cubren_todo_con_solape():
    frases = [{"inicio": 10.0 * i, "fin": 10.0 * i + 9, "texto": "x"} for i in range(120)]   # 20 minutos
    tramos = estructura._tramos(frases)
    assert len(tramos) == 3 and tramos[0][0] == 0 and tramos[-1][-1] == 119
    assert tramos[1][0] == 45          # la segunda ventana (8:00) repite las frases desde 7:30


def test_analizar_guarda_json_y_texto_y_el_reporte_lo_incluye(tmp_path, monkeypatch):
    config.guardar({"openai_clave": "sk-1234567890abcdef"})
    n = 600 * 4
    df = pd.DataFrame({"t": np.round(np.arange(n) / 4, 3), "rostro": [True] * n, "pitch": [0.0] * n,
                       "ojos": [0.1] * n, "ancho_rostro": [100] * n,
                       "x": [0.4] * n, "y": [0.3] * n, "w": [0.1] * n, "h": [0.2] * n})
    analisis.guardar(tmp_path, df, Parametros(), {"titulo": "Sermón de prueba", "duracion_analizada": 600.0})
    (tmp_path / "transcripcion.json").write_text(json.dumps({"modelo": "w", "frases": FRASES}))
    consultas = []

    def falso(url, llave, modelo, instrucciones, texto, progreso=None):
        consultas.append((modelo, texto))
        if instrucciones is estructura.INSTRUCCIONES_ESTRUCTURA:
            return ESTRUCTURA
        return EVANGELIO if instrucciones is estructura.INSTRUCCIONES_EVANGELIO else PASAJES[0]

    monkeypatch.setattr(estructura, "consultar_json", falso)
    datos = estructura.analizar(tmp_path)
    assert len(consultas) == 2 + 2                    # estructura, evangelio y dos ventanas de pasajes (10 min)
    assert {m for m, _ in consultas} == {config.LLM_OPENAI_ESTRUCTURA}
    assert any(t.startswith("Título del video: Sermón de prueba") and "[59] (9:50) frase 59" in t for _, t in consultas)
    assert estructura.leer(tmp_path) == datos and datos["modelo"] == config.LLM_OPENAI_ESTRUCTURA
    assert (tmp_path / "estructura.md").read_text().startswith("# Sermón de prueba")

    html = reporte.generar(tmp_path).read_text()
    assert '"estructura":{"modelo"' in html and "Dios permanece fiel" in html
    (tmp_path / "estructura.json").write_text("{roto")     # editado a mano y mal: el reporte sale sin la pestaña
    assert '"estructura":null' in reporte.generar(tmp_path).read_text()


def test_analizar_sin_transcripcion_o_sin_clave(tmp_path):
    with pytest.raises(FileNotFoundError):
        estructura.analizar(tmp_path)
    (tmp_path / "transcripcion.json").write_text(json.dumps({"frases": FRASES}))
    with pytest.raises(lecturas.FaltaLlave):
        estructura.analizar(tmp_path)


def test_el_modelo_sin_temperatura_se_reintenta(monkeypatch):
    """Los modelos con razonamiento rechazan `temperature`: se repite la consulta sin ella."""
    cuerpos = []

    def falso_pedir(url, llave, cuerpo, tipo, progreso=None):
        cuerpos.append(json.loads(cuerpo))
        if "temperature" in cuerpos[-1]:
            raise RuntimeError("HTTP 400 de x: Unsupported value: 'temperature' does not support 0")
        return {"choices": [{"message": {"content": "```json\n{\"ok\": 1}\n```"}}]}

    monkeypatch.setattr(lecturas, "_pedir", falso_pedir)
    assert lecturas.consultar_json("u", "k", "m", "instrucciones", "texto") == {"ok": 1}
    assert len(cuerpos) == 2 and "temperature" not in cuerpos[1]


def test_a_groq_se_le_pide_una_respuesta_larga(monkeypatch):
    """Groq corta la respuesta si no se le pide más y el JSON llega vacío: solo a Groq se
    le manda `max_completion_tokens`, y si el modelo lo rechaza se repite sin él."""
    cuerpos = []

    def falso_pedir(url, llave, cuerpo, tipo, progreso=None):
        cuerpos.append(json.loads(cuerpo))
        return {"choices": [{"message": {"content": "{\"ok\": 1}"}}]}

    monkeypatch.setattr(lecturas, "_pedir", falso_pedir)
    lecturas.consultar_json(config.GROQ_URL, "k", "m", "instrucciones", "texto")
    lecturas.consultar_json(config.OPENAI_URL, "k", "m", "instrucciones", "texto")
    assert cuerpos[0]["max_completion_tokens"] == lecturas.SALIDA_GROQ
    assert "max_completion_tokens" not in cuerpos[1]

    def lo_rechaza(url, llave, cuerpo, tipo, progreso=None):
        cuerpos.append(json.loads(cuerpo))
        if "max_completion_tokens" in cuerpos[-1]:
            raise RuntimeError("HTTP 400 de x: `max_completion_tokens` must be less than or equal to `8192`")
        return {"choices": [{"message": {"content": "{\"ok\": 1}"}}]}

    cuerpos.clear()
    monkeypatch.setattr(lecturas, "_pedir", lo_rechaza)
    assert lecturas.consultar_json(config.GROQ_URL, "k", "m", "instrucciones", "texto") == {"ok": 1}
    assert len(cuerpos) == 2 and "max_completion_tokens" not in cuerpos[1] and cuerpos[1]["temperature"] == 0

    def demasiado_grande(url, llave, cuerpo, tipo, progreso=None):
        cuerpos.append(json.loads(cuerpo))
        raise RuntimeError("HTTP 413 de x: Request too large for model on tokens per minute (TPM)")

    cuerpos.clear()
    monkeypatch.setattr(lecturas, "_pedir", demasiado_grande)
    with pytest.raises(RuntimeError, match="413"):      # se repite una vez sin el máximo, y si sigue sin caber, falla
        lecturas.consultar_json(config.GROQ_URL, "k", "m", "instrucciones", "texto")
    assert len(cuerpos) == 2 and "max_completion_tokens" not in cuerpos[1]
