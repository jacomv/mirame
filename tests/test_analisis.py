import numpy as np
import pandas as pd
import pytest

from mirame import analisis
from mirame.analisis import ABAJO, CONGREGACION, SIN_DATO, Parametros


def fotogramas(pitches, fps=4.0, ojos=None):
    """DataFrame mínimo como el que produce proceso.medir. None = sin rostro."""
    n = len(pitches)
    return pd.DataFrame({
        "t": np.round(np.arange(n) / fps, 3),
        "rostro": [p is not None for p in pitches],
        "pitch": [np.nan if p is None else float(p) for p in pitches],
        "ojos": ojos if ojos is not None else [0.1] * n,
        "ancho_rostro": [100] * n,
    })


def test_clasifica_por_umbral_sobre_la_mediana():
    df = fotogramas([0] * 8 + [30] * 4)       # mediana 0 → abajo desde 15°
    df, base, metodo = analisis.clasificar(df, Parametros())
    assert base == 0 and metodo == "mediana del sermón"
    assert list(df.clase[:8]) == [CONGREGACION] * 8
    assert list(df.clase[8:]) == [ABAJO] * 4


def test_ojos_bajados_cuentan_como_abajo_aunque_la_cabeza_este_recta():
    df = fotogramas([0] * 4, ojos=[0.1, 0.5, 0.9, 0.2])
    df, _, _ = analisis.clasificar(df, Parametros(umbral_ojos=0.45))
    assert list(df.clase) == [CONGREGACION, ABAJO, ABAJO, CONGREGACION]
    df2, _, _ = analisis.clasificar(fotogramas([0] * 4, ojos=[0.9] * 4), Parametros(umbral_ojos=None))
    assert set(df2.clase) == {CONGREGACION}


def test_sin_rostro_y_excluidos():
    df = fotogramas([0, None, 0, 0, 30, 30, 30, 30])
    df, _, _ = analisis.clasificar(df, Parametros(excluir=[(1.0, 2.0)]))
    assert df.clase[1] == SIN_DATO
    assert set(df.clase[4:]) == {"excluido"}


def test_base_manual():
    df, base, metodo = analisis.clasificar(fotogramas([10, 10, 10, 10]), Parametros(base=-20))
    assert (base, metodo) == (-20, "manual")
    assert set(df.clase) == {ABAJO}


def test_por_segundo_mayoria():
    df = fotogramas([0, 0, 0, 30, 30, 30, 30, 0])
    df, base, _ = analisis.clasificar(df, Parametros(base=0))
    seg = analisis.por_segundo(df, base + 15)
    assert list(seg.clase) == [CONGREGACION, ABAJO]


def test_episodios_y_vistazos():
    df = fotogramas([0] * 4 + [30] * 8 + [0] * 4 + [30] * 2 + [0] * 4)
    df, _, _ = analisis.clasificar(df, Parametros(base=0))
    eps = analisis.episodios(df, 4.0)
    assert [e["duracion"] for e in eps] == [2.0, 0.5]
    assert eps[0]["inicio"] == 1.0


def test_miradas_no_se_cortan_por_un_parpadeo():
    # 3 s mirando, 0,5 s abajo (parpadeo), 3 s mirando, 2 s abajo, 2 s mirando
    df = fotogramas([0] * 12 + [30] * 2 + [0] * 12 + [30] * 8 + [0] * 8)
    df, _, _ = analisis.clasificar(df, Parametros(base=0))
    m = analisis.miradas(df, 4.0)
    assert [x["duracion"] for x in m] == [6.5, 2.0]
    assert m[0]["inicio"] == 0.0


def test_miradas_se_cortan_al_perder_el_rostro():
    df = fotogramas([0] * 8 + [None] * 8 + [0] * 8)
    df, _, _ = analisis.clasificar(df, Parametros(base=0))
    assert [x["duracion"] for x in analisis.miradas(df, 4.0)] == [2.0, 2.0]


def test_en_tramos():
    assert list(analisis.en_tramos([0.5, 1.5, 3.0], [(1, 2), (3, 4)])) == [False, True, True]


@pytest.mark.parametrize("pct_sin, confiable", [(10, True), (40, False)])
def test_advertencia_poco_confiable(pct_sin, confiable):
    n = 100
    sin = int(n * pct_sin / 100)
    df = fotogramas([None] * sin * 4 + [0] * (n - sin) * 4)
    df, base, metodo = analisis.clasificar(df, Parametros())
    seg = analisis.por_segundo(df, base + 15)
    r = analisis.resumir(df, seg, Parametros(), base, metodo, {})
    assert r["poco_confiable"] is (not confiable)


def test_avisa_si_demasiado_sermon_quedo_marcado_como_oracion(tmp_path):
    import json

    df = fotogramas([0] * 400)                                   # 100 s
    video = {"titulo": "x", "duracion_analizada": 100.0}
    (tmp_path / "lecturas.json").write_text(json.dumps({"lecturas": [], "oraciones": [{"inicio": 0, "fin": 10}]}))
    r = analisis.guardar(tmp_path, df, Parametros(), video)
    assert r["oracion"]["segundos"] == 10 and r["segundos_excluidos"] == 10 and r["advertencias"] == []
    (tmp_path / "lecturas.json").write_text(json.dumps({"lecturas": [], "oraciones": [
        {"inicio": 0, "fin": 10}, {"inicio": 40, "fin": 60}]}))
    r = analisis.guardar(tmp_path, analisis.leer_fotogramas(tmp_path), Parametros(), video)
    assert len(r["advertencias"]) == 1 and "marcados como oración (en 0:00, 0:40)" in r["advertencias"][0]


def test_guardar_y_recalcular_dan_lo_mismo(tmp_path):
    df = fotogramas([0] * 20 + [30] * 8 + [0] * 12)
    r1 = analisis.guardar(tmp_path, df, Parametros(), {"titulo": "x"})
    df2 = analisis.leer_fotogramas(tmp_path)
    r2 = analisis.guardar(tmp_path, df2, analisis.parametros_de(r1), {"titulo": "x"})
    for k in ("pct_congregacion", "pct_abajo", "episodios_abajo", "contacto"):
        assert r1[k] == r2[k]


# ---------------------------------------------------------------- método 3
def test_un_parpadeo_no_cuenta_como_abajo():
    # Un solo fotograma con los ojos cerrados (0,25 s) es un parpadeo; dos seguidos ya cuentan.
    ojos = [0.1] * 4 + [0.9] + [0.1] * 4 + [0.9, 0.9] + [0.1] * 4
    df, _, _ = analisis.clasificar(fotogramas([0] * len(ojos), ojos=ojos), Parametros(base=0))
    assert df.clase[4] == CONGREGACION
    assert list(df.clase[9:11]) == [ABAJO, ABAJO]


def test_ojos_cerrados_con_la_cabeza_levantada_no_es_leer():
    df, _, _ = analisis.clasificar(fotogramas([-15] * 4, ojos=[0.9] * 4), Parametros(base=0))
    assert set(df.clase) == {CONGREGACION}


def test_calibra_con_los_ojos_arriba():
    # 60 % del tiempo leyendo con la cabeza a +12°: la mediana general queda sesgada,
    # la de los fotogramas con ojos arriba no.
    pitches = [0] * 400 + [12] * 600
    ojos = [0.1] * 400 + [0.6] * 600
    _, base, metodo = analisis.clasificar(fotogramas(pitches, ojos=ojos), Parametros())
    assert base == 0 and metodo == "mediana con los ojos arriba"
    _, base, _ = analisis.clasificar(fotogramas(pitches, ojos=ojos), Parametros(calibrar_ojos=None))
    assert base == 12


def test_intervalo_es_repetible_y_contiene_el_valor(tmp_path):
    rng = np.random.default_rng(1)
    pitches = list(np.where(rng.random(4 * 600) < 0.3, 30, 0))
    r = analisis.guardar(tmp_path, fotogramas(pitches), Parametros(), {})
    lo, hi = r["intervalo_congregacion"]
    assert lo <= r["pct_congregacion"] <= hi
    assert analisis.guardar(tmp_path, fotogramas(pitches), Parametros(), {})["intervalo_congregacion"] == [lo, hi]
    assert set(r["sensibilidad"]) == {"umbral_12", "umbral_18"}


def test_recalcular_conserva_la_calibracion_por_tramo(tmp_path):
    r = analisis.guardar(tmp_path, fotogramas([0] * 40), Parametros(calibrar=(0.0, 5.0)), {})
    assert analisis.parametros_de(r).calibrar == (0.0, 5.0)


def test_en_la_franja_dudosa_deciden_los_ojos():
    # Cabeza a +17° (cerca del umbral de 15°): con los ojos arriba mira a la gente;
    # con los ojos algo bajos, lee. Pasada la franja (+25°) es abajo siempre.
    df, _, _ = analisis.clasificar(fotogramas([17, 17, 17, 17, 25, 25], ojos=[0.1, 0.1, 0.3, 0.3, 0.1, 0.1]),
                                   Parametros(base=0))
    assert list(df.clase) == [CONGREGACION, CONGREGACION, ABAJO, ABAJO, ABAJO, ABAJO]
