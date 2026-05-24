# 2026-05-24 Upstream Sync to v0.51.124

## Overview

Merged current `origin/master` from `nesquena/hermes-webui` into the local
`master` branch while preserving the local OpenCode provider detection behavior.
The upstream target was `66de2367` / `v0.51.124`.

## Requirements

- Bring in the latest WebUI features, vulnerability-adjacent hardening, and bug
  fixes from upstream.
- Preserve local fork behavior, especially shared `OPENCODE_API_KEY` detection.
- Make WebUI open and run against
  `C:\Users\downl\Desktop\hermes-agent-upstream-sync`.
- Avoid committing machine-local secrets or private state.

## Decisions

- Used `origin/master` as the authoritative upstream source.
- Kept upstream's expanded native Windows `start.ps1` implementation instead of
  the older local bootstrap wrapper.
- Kept local `OPENCODE_API_KEY` support and added regression coverage so future
  upstream syncs do not drop it silently.
- Updated runtime-local state outside the repo:
  - `C:\Users\downl\.hermes\webui\last_workspace.txt`
  - `C:\Users\downl\.hermes\config.yaml` `terminal.cwd`

## Changed Files

- Upstream merge: WebUI code, static assets, tests, docs, and release notes
  through `v0.51.124`.
- `api/config.py`: preserved shared `OPENCODE_API_KEY` detection for both
  OpenCode Zen and OpenCode Go.
- `tests/test_opencode_providers.py`: added shared key regression coverage and
  made source reads UTF-8 explicit for Windows.
- `tests/test_windows_native_start.py`: updated the local Windows launcher test
  to match the new upstream `start.ps1` contract.
- `CHANGELOG.md`: recorded the preserved local OpenCode detection under
  `Unreleased`.

## Verification

Commands run:

- `git fetch origin --prune`
- `git fetch zapabob --prune`
- `git merge --no-ff origin/master`
- `uv run --python 3.12 --with pytest --with pytest-timeout --with pyyaml pytest tests/test_opencode_providers.py tests/test_bootstrap_python_selection.py tests/test_windows_native_start.py tests/test_bootstrap_discover_agent.py tests/test_updates.py tests/test_update_checker.py -q`
  - Result: `48 passed`
- `uv run --python 3.12 --with pytest --with pytest-timeout --with pyyaml pytest tests/test_update_banner_fixes.py tests/test_update_check_ui.py tests/test_static_asset_compression_and_cache.py tests/test_2735_open_in_vscode.py tests/test_inflight_send_start_race.py tests/test_window_function_collision.py tests/test_issue2713_streaming_segment_flush.py tests/test_issue2233_sqlite_connection_leak.py -q`
  - Result: `127 passed, 1 skipped`
- `git diff --cached --check`
  - Result: passed
- `PYTHONUTF8=1 HERMES_WEBUI_AGENT_DIR=C:\Users\downl\Desktop\hermes-agent-upstream-sync uv run --python 3.12 --with pytest --with pytest-timeout --with pyyaml pytest --collect-only -q --ignore=tests/test_terminal_process_cleanup.py`
  - Result: `6341 tests collected`
  - Note: Windows-only collection excludes the POSIX `fcntl` terminal process
    cleanup test.
- PowerShell parser check for `start.ps1`
  - Result: passed
- Temporary `start.ps1` smoke on `127.0.0.1:8799`
  - Result: `/health` returned `status: ok`
  - Startup banner confirmed:
    - agent dir: `C:\Users\downl\Desktop\hermes-agent-upstream-sync`
    - workspace: `C:\Users\downl\Desktop\hermes-agent-upstream-sync`
- Production local start on `127.0.0.1:8787`
  - Result: `/health` returned `status: ok`
  - Startup log confirmed:
    - agent dir: `C:\Users\downl\Desktop\hermes-agent-upstream-sync`
    - workspace: `C:\Users\downl\Desktop\hermes-agent-upstream-sync`

## Residual Risks

- The full test execution was not run end-to-end on Windows. Collection passes
  with UTF-8 enabled when the POSIX-only `fcntl` test is ignored.
- Some tests still depend on POSIX assumptions or locale-default UTF-8 unless
  `PYTHONUTF8=1` is set.
- Runtime state changes were intentionally local and should not be moved into
  tracked repository files.

## Next Actions

- Commit the merge once final status is clean.
- Push to the writable `zapabob/master` remote if publishing is desired.
