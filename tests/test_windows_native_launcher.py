from __future__ import annotations

import subprocess
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NATIVE_LAUNCHER = REPO_ROOT / "scripts" / "windows" / "start-hermes-webui-native.ps1"


def _read_launcher() -> str:
    return NATIVE_LAUNCHER.read_text(encoding="utf-8")


def test_native_launcher_resolves_password_without_repo_env_secret():
    script = _read_launcher()

    assert "function Resolve-WebUiPassword" in script
    assert "HERMES_WEBUI_PASSWORD_FILE" in script
    assert 'Join-Path $HermesHome ".env"' in script
    assert 'Read-DotEnvValue -Path $WebUiEnvPath -Name "HERMES_WEBUI_PASSWORD"' in script
    assert "$env:HERMES_WEBUI_PASSWORD = $resolvedPassword.Password" in script
    assert '$env:HERMES_WEBUI_PRESERVE_ENV = "1"' in script
    assert "Injected HERMES_WEBUI_PASSWORD from $($resolvedPassword.Source)." in script


def test_native_launcher_env_parser_handles_bom_and_export_lines():
    script = _read_launcher()

    assert "function Read-DotEnvValue" in script
    assert ".TrimStart([char]0xFEFF)" in script
    assert '-replace "^export\\s+", ""' in script
    assert 'if ($value -match \'^"(.*)"$\')' in script
    assert 'if ($value -match "^(.*)"$")' not in script


def test_native_launcher_can_open_browser_after_readiness():
    script = _read_launcher()

    assert "[switch]$Open" in script
    assert "function Start-WebUiBrowserOpener" in script
    assert "Invoke-WebRequest -UseBasicParsing -Uri `$url -TimeoutSec 2" in script
    assert "Start-Process `$url" in script
    assert "HERMES_WEBUI_OPEN_ON_START" in script
    assert "Test-TruthyEnv" in script
    assert "WindowStyle" in script
    assert "Hidden" in script


def test_native_launcher_prefers_dotvenv_without_forcing_default_model():
    script = _read_launcher()

    assert '".venv\\Scripts\\python.exe"' in script
    assert '"venv\\Scripts\\python.exe"' in script
    assert "$AgentPythonCandidates | Where-Object" in script
    assert "$env:HERMES_WEBUI_DEFAULT_MODEL =" not in script


def test_native_launcher_does_not_print_password_value():
    script = _read_launcher()

    forbidden = (
        "Write-Host $env:HERMES_WEBUI_PASSWORD",
        "Write-Host $resolvedPassword.Password",
        "Write-Output $env:HERMES_WEBUI_PASSWORD",
        "Write-Output $resolvedPassword.Password",
    )
    for needle in forbidden:
        assert needle not in script


def test_native_launcher_passes_parser_when_powershell_is_available():
    powershell = None
    for candidate in ("pwsh", "powershell"):
        if not shutil.which(candidate):
            continue
        result = subprocess.run(
            [candidate, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            powershell = candidate
            break
    if not powershell:
        return

    subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-Command",
            f"$null = [scriptblock]::Create((Get-Content -Raw '{NATIVE_LAUNCHER.as_posix()}'))",
        ],
        check=True,
        cwd=REPO_ROOT,
    )
