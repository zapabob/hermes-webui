import pathlib


REPO = pathlib.Path(__file__).parent.parent


def test_start_ps1_loads_dotenv_and_runs_bootstrap():
    script = (REPO / "start.ps1").read_text(encoding="utf-8")
    assert ".env" in script
    assert "bootstrap.py" in script
    assert "--no-browser" in script
    assert "HERMES_WEBUI_PYTHON" in script


def test_bootstrap_no_longer_blocks_native_windows():
    src = (REPO / "bootstrap.py").read_text(encoding="utf-8")
    assert "Please run it from Linux, macOS, or inside WSL2" not in src
    assert "Native Windows bootstrap cannot run" in src
