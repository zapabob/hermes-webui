#!/usr/bin/env python3
"""Smoke checks for fork-only features after upstream merge."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def check_irodori_tts() -> None:
    from api.routes import (
        _normalize_irodori_base_url,
        _resolve_irodori_tts_settings,
        _safe_irodori_voice_id,
    )

    assert _safe_irodori_voice_id("irodori-voice-1")
    assert not _safe_irodori_voice_id("../escape")
    assert _normalize_irodori_base_url("http://127.0.0.1:8088/").startswith("http://127.0.0.1:8088")
    cfg = _resolve_irodori_tts_settings()
    for key in ("base_url", "model", "voice", "speed"):
        assert key in cfg, f"missing {key} in Irodori settings"
    print("irodori_tts: ok")


def check_opencode_shared_key() -> None:
    from api.providers import _PROVIDER_ENV_VAR_ALIASES, _provider_has_key

    zen_aliases = _PROVIDER_ENV_VAR_ALIASES.get("opencode-zen", ())
    go_aliases = _PROVIDER_ENV_VAR_ALIASES.get("opencode-go", ())
    assert "OPENCODE_API_KEY" in zen_aliases
    assert "OPENCODE_API_KEY" in go_aliases

    os.environ["OPENCODE_API_KEY"] = "test-shared-key"
    try:
        assert _provider_has_key("opencode-zen")
        assert _provider_has_key("opencode-go")
    finally:
        os.environ.pop("OPENCODE_API_KEY", None)
    print("opencode_shared_key: ok")


def check_windows_launcher() -> None:
    ps1 = REPO / "scripts" / "windows" / "start-hermes-webui-native.ps1"
    assert ps1.is_file(), "native Windows launcher missing"
    text = ps1.read_text(encoding="utf-8")
    for needle in (
        "Resolve-WebUiPassword",
        "HERMES_WEBUI_PASSWORD",
        "[switch]$Open",
        "start.ps1",
    ):
        assert needle in text, f"missing launcher feature: {needle}"
    print("windows_launcher: ok")


def check_static_irodori_hooks() -> None:
    ui = (REPO / "static" / "ui.js").read_text(encoding="utf-8")
    boot = (REPO / "static" / "boot.js").read_text(encoding="utf-8")
    assert "irodori" in ui.lower()
    assert "_irodoriTtsPayload" in ui or "irodori" in ui
    assert "irodori" in boot.lower()
    print("static_irodori_hooks: ok")


def main() -> int:
    checks = (
        check_irodori_tts,
        check_opencode_shared_key,
        check_windows_launcher,
        check_static_irodori_hooks,
    )
    for fn in checks:
        fn()
    print(f"all {len(checks)} fork smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
