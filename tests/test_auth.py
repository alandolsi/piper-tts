"""API-Key-Schutz fuer /tts. TestClient ohne `with` startet die Startup-Events
nicht - so laesst sich der Schutz ohne Piper-Modell pruefen."""
import importlib

import pytest
from fastapi.testclient import TestClient

KEY = "test-key-123"


def load_app(monkeypatch, key, tmp_path):
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    if key is None:
        monkeypatch.delenv("PIPER_API_KEY", raising=False)
    else:
        monkeypatch.setenv("PIPER_API_KEY", key)
    import app as app_module

    module = importlib.reload(app_module)

    # Nie ein lokales "piper"-Programm starten: Synthese durch Platzhalter ersetzen.
    async def fake_synthesize(text, output_path):
        output_path.write_bytes(b"RIFF")

    monkeypatch.setattr(module, "_synthesize_to_file", fake_synthesize)
    return module.app


@pytest.fixture
def client(monkeypatch, tmp_path):
    return TestClient(load_app(monkeypatch, KEY, tmp_path), raise_server_exceptions=False)


def test_tts_ohne_key_401(client):
    assert client.post("/tts", json={"text": "Hallo"}).status_code == 401


def test_tts_mit_falschem_key_401(client):
    res = client.post("/tts", json={"text": "Hallo"}, headers={"X-API-Key": "falsch"})
    assert res.status_code == 401


def test_tts_mit_key_liefert_audio(client):
    res = client.post("/tts", json={"text": "Hallo"}, headers={"X-API-Key": KEY})
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/wav"


def test_health_bleibt_offen(client):
    assert client.get("/health").status_code == 200


def test_api_doku_abgeschaltet(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path


def test_ohne_konfigurierten_key_wird_abgelehnt(monkeypatch, tmp_path):
    c = TestClient(load_app(monkeypatch, None, tmp_path), raise_server_exceptions=False)
    res = c.post("/tts", json={"text": "Hallo"}, headers={"X-API-Key": "irgendwas"})
    assert res.status_code == 503


def test_textlaenge_begrenzt(client):
    res = client.post("/tts", json={"text": "a" * 5001}, headers={"X-API-Key": KEY})
    assert res.status_code == 422
