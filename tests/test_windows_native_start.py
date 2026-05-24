import pathlib


REPO = pathlib.Path(__file__).parent.parent


def test_start_ps1_loads_dotenv_and_runs_server_directly():
    script = (REPO / "start.ps1").read_text(encoding="utf-8")
    assert ".env" in script
    assert "server.py" in script
    assert "HERMES_WEBUI_PYTHON" in script
    assert "HERMES_WEBUI_AGENT_DIR" in script
    assert "hermes_cli" in script
    assert "venv\\Scripts\\python.exe" in script
    assert "TryParse" in script


def test_bootstrap_native_windows_requires_existing_agent_before_install_fallback():
    src = (REPO / "bootstrap.py").read_text(encoding="utf-8")
    assert "Please run it from Linux, macOS, or inside WSL2" not in src
    assert "Native Windows bootstrap cannot run" in src
    assert "HERMES_WEBUI_AGENT_DIR" in src
