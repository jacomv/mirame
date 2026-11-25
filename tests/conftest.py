import pytest


@pytest.fixture(autouse=True)
def datos_temporales(tmp_path, monkeypatch):
    """Cada prueba usa su propia carpeta de datos y no ve claves del entorno real."""
    monkeypatch.setenv("MIRAME_DATOS", str(tmp_path / "datos"))
    for v in ("GROQ_API_KEY", "MIRAME_LLM_URL", "MIRAME_LLM_KEY", "MIRAME_LLM_MODELO", "MIRAME_WHISPER_MODELO",
              "OPENAI_API_KEY", "MIRAME_OPENAI_MODELO"):
        monkeypatch.delenv(v, raising=False)
    return tmp_path / "datos"
