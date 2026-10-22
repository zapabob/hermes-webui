"""Coverage for the Irodori TTS engine on /api/tts."""

import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import api.routes as routes


class _FakeHandler:
    def __init__(self, body: bytes, command: str = "POST", headers=None, client="9.9.9.9"):
        self.command = command
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.headers = headers or {}
        self.headers.setdefault("Content-Length", str(len(body)))
        self.client_address = (client, 12345)
        self.status = None
        self.sent_headers = {}

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.sent_headers[key] = value

    def end_headers(self):
        pass

    def payload(self):
        try:
            return json.loads(self.wfile.getvalue().decode("utf-8"))
        except Exception:
            return None


def _post(body_dict, **kw):
    return _FakeHandler(json.dumps(body_dict).encode(), **kw)


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    import api.auth as _auth

    monkeypatch.setattr(_auth, "is_auth_enabled", lambda: False)
    monkeypatch.setattr(routes, "is_auth_enabled", lambda: False, raising=False)
    monkeypatch.delenv("HERMES_WEBUI_TRUST_FORWARDED_FOR", raising=False)
    monkeypatch.delenv("IRODORI_API_KEY", raising=False)
    monkeypatch.delenv("IRODORI_TTS_ALLOW_REMOTE_API_KEY", raising=False)
    if hasattr(routes._handle_tts, "_tts_limiter"):
        del routes._handle_tts._tts_limiter
    yield
    if hasattr(routes._handle_tts, "_tts_limiter"):
        del routes._handle_tts._tts_limiter


def test_irodori_rejects_invalid_speed(monkeypatch):
    monkeypatch.setattr(
        routes,
        "_resolve_irodori_tts_settings",
        lambda: {
            "base_url": "http://127.0.0.1:8088",
            "model": "irodori-tts",
            "voice": "none",
            "speed": 1.0,
            "api_key": "",
        },
    )
    h = _post({"text": "hello", "engine": "irodori", "speed": 9.9}, client="9.9.9.1")
    routes._handle_tts(h, None)
    assert h.status == 400
    assert "speed" in (h.payload() or {}).get("error", "")


def test_irodori_rejects_invalid_voice(monkeypatch):
    monkeypatch.setattr(
        routes,
        "_resolve_irodori_tts_settings",
        lambda: {
            "base_url": "http://127.0.0.1:8088",
            "model": "irodori-tts",
            "voice": "none",
            "speed": 1.0,
            "api_key": "",
        },
    )
    h = _post({"text": "hello", "engine": "irodori", "voice": "../../etc/passwd"}, client="9.9.9.2")
    routes._handle_tts(h, None)
    assert h.status == 400
    assert "voice" in (h.payload() or {}).get("error", "")


def test_irodori_happy_path_streams_mp3(monkeypatch):
    monkeypatch.setattr(
        routes,
        "_resolve_irodori_tts_settings",
        lambda: {
            "base_url": "http://127.0.0.1:8088",
            "model": "irodori-tts",
            "voice": "hakua",
            "speed": 1.0,
            "api_key": "local-key",
        },
    )
    captured = {}

    class _Resp:
        def __init__(self):
            self._chunks = [b"ID3fakeaudio", b""]
            self._i = 0

        def read(self, n=-1):
            c = self._chunks[self._i] if self._i < len(self._chunks) else b""
            self._i += 1
            return c

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _fake_urlopen(req, **_kw):
        captured["url"] = req.full_url
        captured["auth"] = req.get_header("Authorization")
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp()

    monkeypatch.setattr(routes, "_tts_open", _fake_urlopen)

    h = _post({"text": "こんにちは", "engine": "irodori", "voice": "hakua", "speed": 1.1}, client="9.9.9.3")
    routes._handle_tts(h, None)

    assert h.status == 200
    assert h.sent_headers.get("Content-Type") == "audio/mpeg"
    assert h.wfile.getvalue() == b"ID3fakeaudio"
    assert captured["url"] == "http://127.0.0.1:8088/v1/audio/speech"
    assert captured["auth"] == "Bearer local-key"
    assert captured["body"] == {
        "model": "irodori-tts",
        "input": "こんにちは",
        "voice": "hakua",
        "response_format": "mp3",
        "speed": 1.1,
    }


def test_irodori_remote_api_key_not_sent_without_opt_in(monkeypatch):
    monkeypatch.setattr(
        routes,
        "_resolve_irodori_tts_settings",
        lambda: {
            "base_url": "https://example.com:8088",
            "model": "irodori-tts",
            "voice": "none",
            "speed": 1.0,
            "api_key": "secret",
        },
    )

    class _Resp:
        def __init__(self):
            self._chunks = [b"audio", b""]
            self._i = 0

        def read(self, n=-1):
            c = self._chunks[self._i] if self._i < len(self._chunks) else b""
            self._i += 1
            return c

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    captured = {}

    def _fake_urlopen(req, **_kw):
        captured["auth"] = req.get_header("Authorization")
        return _Resp()

    monkeypatch.setattr(routes, "_tts_open", _fake_urlopen)

    h = _post({"text": "hello", "engine": "irodori"}, client="9.9.9.4")
    routes._handle_tts(h, None)

    assert h.status == 200
    assert captured["auth"] is None


def test_normalize_irodori_base_url_strips_openai_suffixes():
    assert routes._normalize_irodori_base_url("http://127.0.0.1:8088/v1/audio/speech") == "http://127.0.0.1:8088"
    assert routes._normalize_irodori_base_url("http://127.0.0.1:8088/v1") == "http://127.0.0.1:8088"


@pytest.mark.parametrize("engine", [None, "", "irodori"])
def test_irodori_persisted_engine_and_configured_voice(monkeypatch, engine):
    """The official persisted-engine route must retain the fork engine's defaults."""
    monkeypatch.setattr(routes, "load_settings", lambda: {"tts_engine": "irodori"})
    monkeypatch.setattr(routes, "_resolve_irodori_tts_settings", lambda: {
        "base_url": "http://127.0.0.1:8088", "model": "irodori-tts",
        "voice": "hakua", "speed": 1.0, "api_key": "",
    })
    captured = {}

    class Response(io.BytesIO):
        headers = {"Content-Type": "audio/mpeg"}

    def open_audio(req, **kwargs):
        captured.update(json.loads(req.data))
        return Response(b"ID3test")

    monkeypatch.setattr(routes, "_tts_open", open_audio)
    body = {"text": "hello", "voice": "none"} if engine != "irodori" else {"text": "hello"}
    if engine is not None:
        body["engine"] = engine
    handler = _post(body)
    routes._handle_tts(handler, None)

    assert handler.status == 200
    assert captured["voice"] == ("hakua" if engine == "irodori" else "none")
    assert handler.wfile.getvalue() == b"ID3test"


def test_irodori_profile_mismatch_does_not_read_config(monkeypatch):
    import api.profiles as profiles

    monkeypatch.setattr(profiles, "get_active_profile_name", lambda: "beta")
    monkeypatch.setattr(profiles, "_profiles_match", lambda left, right: left == right)

    def unexpected_config():
        pytest.fail("a stale playback must not read another profile's TTS config")

    monkeypatch.setattr(routes, "_resolve_irodori_tts_settings", unexpected_config)
    handler = _post({"text": "hello", "engine": "irodori", "profile": "alpha"})
    routes._handle_tts(handler, None)
    assert handler.status == 409
    assert not hasattr(routes._handle_tts, "_tts_limiter")


def test_irodori_uses_official_no_redirect_transport(monkeypatch):
    """Exercise the shared urllib guard against a disposable loopback responder."""
    requests = []

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.command, self.path))
            self.send_response(302)
            self.send_header("Location", "/redirected")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            requests.append((self.command, self.path))
            self.send_response(200)
            self.send_header("Content-Length", "8")
            self.end_headers()
            self.wfile.write(b"ID3audio")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), RedirectHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    monkeypatch.setattr(routes, "_resolve_irodori_tts_settings", lambda: {
        "base_url": f"http://127.0.0.1:{server.server_port}", "model": "irodori-tts",
        "voice": "hakua", "speed": 1.0, "api_key": "fixture-only-key",
    })
    try:
        handler = _post({"text": "hello", "engine": "irodori"})
        routes._handle_tts(handler, None)
        assert handler.status == 502
        assert requests == [("POST", "/v1/audio/speech")]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
