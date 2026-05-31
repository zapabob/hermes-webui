from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MERGE_SCRIPT = REPO_ROOT / "scripts" / "merge_official_updates.py"


def test_merge_script_forces_utf8_console_output():
    src = MERGE_SCRIPT.read_text(encoding="utf-8")

    assert "def configure_stdio()" in src
    assert 'reconfigure(encoding="utf-8", errors="replace")' in src
    assert "configure_stdio()" in src[src.index('if __name__ == "__main__":') :]


def test_merge_script_decodes_git_output_as_utf8_with_replacement():
    src = MERGE_SCRIPT.read_text(encoding="utf-8")

    assert 'encoding="utf-8"' in src
    assert 'errors="replace"' in src
