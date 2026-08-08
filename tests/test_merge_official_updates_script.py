from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


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


def test_merge_script_has_checkpoint_and_fork_hints():
    src = MERGE_SCRIPT.read_text(encoding="utf-8")

    assert "CHECKPOINT_NAME" in src
    assert "FORK_PRESERVE_HINTS" in src
    assert "api/routes.py" in src
    assert "Irodori" in src
    assert "--resume" in src
    assert "--abort" in src


def test_merge_script_uses_tqdm_with_fallback():
    src = MERGE_SCRIPT.read_text(encoding="utf-8")

    assert "def _try_import_tqdm()" in src
    assert "class Progress:" in src


def test_parse_conflict_files_extracts_paths():
    from scripts.merge_official_updates import parse_conflict_files

    sample = """
Auto-merging CHANGELOG.md
CONFLICT (content): Merge conflict in CHANGELOG.md
Auto-merging CONTRIBUTORS.md
CONFLICT (content): Merge conflict in CONTRIBUTORS.md
"""
    paths = parse_conflict_files(sample)
    assert paths == ["CHANGELOG.md", "CONTRIBUTORS.md"]


def test_checkpoint_roundtrip(tmp_path: Path):
    from scripts.merge_official_updates import MergeCheckpoint, load_checkpoint, save_checkpoint

    repo = tmp_path
    cp = MergeCheckpoint(repo=str(repo), phase="preview", upstream_tag="v0.51.660")
    save_checkpoint(repo, cp)
    loaded = load_checkpoint(repo)
    assert loaded is not None
    assert loaded.upstream_tag == "v0.51.660"
    assert loaded.phase == "preview"


@pytest.mark.usefixtures()  # avoid session autouse test_server from conftest
def test_merge_script_dry_run_smoke():
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            str(MERGE_SCRIPT),
            "--dry-run",
            "--remote-name",
            "upstream",
            "--log-limit",
            "3",
            "--allow-tracked-changes",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dry run complete" in result.stdout
    assert re.search(
        r"Official upstream/master: [0-9a-f]+ \((?:exp-)?v\d+\.\d+\.\d+\)",
        result.stdout,
    )
