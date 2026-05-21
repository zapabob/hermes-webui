# Native Windows Startup Closeout

Date: 2026-05-21
Agent: Codex
Repo: hermes-webui

## Overview

Enabled `bootstrap.py` and the local launcher path to run on native Windows,
without requiring WSL2. Added a PowerShell launcher, Windows Python discovery,
Windows symlink fallback behavior for tests, and docs that describe the native
Windows flow.

## Background

The initial native Windows command failed immediately:

```text
python bootstrap.py --no-browser --skip-agent-install
[bootstrap] ERROR: Native Windows is not supported for this bootstrap yet.
```

The checkout already had `.env` pointing at the local Hermes Agent checkout:

```text
HERMES_WEBUI_AGENT_DIR=C:/Users/downl/Desktop/hermes-agent-main/hermes-agent-main
HERMES_WEBUI_STATE_DIR=C:/Users/downl/.hermes/webui
```

No secrets were printed.

## Changes

- `bootstrap.py`
  - Removed the native-Windows hard block.
  - Kept POSIX installer use off native Windows, with a clear error if Hermes
    Agent is missing there.
  - Preferred local and agent virtualenv interpreters, then the current Python,
    while avoiding Windows App Execution Alias shims.
- `start.ps1`
  - Added a native PowerShell launcher that loads `.env` and runs bootstrap.
- `api/config.py`
  - Added native Windows `.venv\\Scripts\\python.exe` discovery.
  - Preferred current `sys.executable` when it is real and not a WindowsApps
    alias.
- `tests/conftest.py`
  - Added Windows venv Python discovery.
  - Falls back from directory symlink to `copytree` on systems without symlink
    privilege.
- Docs and changelog
  - Updated README, onboarding docs, agent checklist, and changelog.
- Tests
  - Added static coverage for `start.ps1` and Windows bootstrap behavior.

## Verification

Focused tests passed using H: for temporary test state because C: was nearly
full:

```text
python -m pytest tests/test_onboarding_static.py tests/test_windows_native_start.py tests/test_bootstrap_python_selection.py -q -o addopts='' -p no:cacheprovider --basetemp=H:\codex-tmp\hermes-webui-pytest\basetemp
10 passed in 8.89s
```

Native Windows launcher proof with the default `.env` state path:

```text
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 8794
[bootstrap] Web UI is ready: http://localhost:8794
GET http://127.0.0.1:8794/health -> status ok
STOPPED=1
```

Final rerun:

```text
python -m pytest tests/test_onboarding_static.py tests/test_windows_native_start.py tests/test_bootstrap_python_selection.py -q -o addopts='' -p no:cacheprovider --basetemp=H:\codex-tmp\hermes-webui-final-pytest\basetemp
10 passed in 6.86s

powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 8795
GET http://127.0.0.1:8795/health -> {"status":"ok","sessions":0,...}
STOPPED=1
```

## Residual Risks

- C: was almost full during initial verification. After removing generated
  temp/test/install scratch directories, it recovered to about 5 GB free, but
  long-running WebUI/test work should still prefer a larger state/temp path when
  available.
- WSL2 was recovered separately and is available, but this change keeps native
  Windows startup as the primary path.
