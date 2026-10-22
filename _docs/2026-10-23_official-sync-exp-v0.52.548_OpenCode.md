# Official upstream integration through exp-v0.52.548

## Overview and objective

Integrate the latest official Hermes WebUI features, security maintenance, and
bug fixes through the existing Python merge tooling, preserve fork-only
features, and adapt those features to the official APIs. Implementation agent:
OpenCode, OpenAI `openai/gpt-6.1-sol`. The working-tree integration and targeted
verification are complete. The merge was resolved and initially handed off
uncommitted; the user subsequently authorised committing and pushing `master`.

## Background and requirements

| ID | Acceptance criterion | Implementation / evidence |
| --- | --- | --- |
| SYNC-01 | Include official master at the fetched revision | `6a8d34cd4974cec0c23632c8d1d3168fdee380cd`, `exp-v0.52.548`; existing Python scripts |
| SYNC-02 | Preserve Irodori TTS and follow official playback/request APIs | `api/routes.py`, `static/ui.js`, `static/boot.js`; behavioral playback and endpoint regressions |
| SYNC-03 | Preserve shared OpenCode credentials and provider-specific keys | Official `api/providers.py` implementation and adjacent provider tests |
| SYNC-04 | Preserve native Windows wrapper and upstream discovery | `start.ps1`, existing password / browser wrapper and Windows tests |
| SYNC-05 | Preserve fork remote-tag update gating and official updater hardening | `api/updates.py`, union of fork and upstream update tests |
| SYNC-06 | Verify using disposable state; record limitations honestly | Repository test runner, baseline/red/green evidence, browser checks |

## Applicable standards and Contract Routing

Applied PC-wide common engineering, Implementation Start Gate, Skill Selection,
DeepResearch, Security, Application Development, WebApp Development, Frontend
Design, and Python SOPs. Applied the injected deepresearch-defense-standard and
milspec-codex-standard baselines plus hermes-webui-upstream-redteam (official-sync
phase only) and plan-mode. The canonical pre-implementation prompt was read;
conflicting identity, tool, environment, and release instructions do not override
the active harness or project rules. No formal MILSPEC compliance is claimed.

Public routing: `AGENTS.md`, `CONTRIBUTING.md`, `docs/CONTRACTS.md`,
`docs/GUIDELINES.md`, `ARCHITECTURE.md`, `TESTING.md`, `DESIGN.md`,
`docs/UIUX-GUIDE.md`, `docs/onboarding-agent-checklist.md`, and
`docs/architecture/agent-api-contract.md`. TTS presentation state is owned by the
official browser playback generation and shared request scheduler; a captured
profile travels with each queued/retried request and the server refuses a
mismatch before reading credentials/configuration or charging the rate limiter.
Agent source/API coupling remains the official compatibility boundary.

## Assumptions and decisions

Initial HEAD was `014ae026`, tracking `origin/master`; tracked files were clean.
The pre-existing untracked `.cursor/` directory is user work. The fetched
upstream was 3,476 commits ahead, with 42 fork-only commits and 1,062 differing
files. The source checkpoint is `7f279423` (`exp-v0.52.180`). The official stable
release is `v0.52.492`, not the experimental branch tip.

Used `scripts/merge_official_updates.py --dry-run` for fetch/checkpoint/preview,
then `scripts/sync_upstream_preserve_custom.py --skip-fetch --allow-dirty --merge`
for a no-commit integration. The dirty override was needed only for the existing
untracked `.cursor/`, not for tracked modifications. The original integration
request did not authorise a commit, push, release or production service restart,
so the verified merge was initially left pending. Publication was authorised in
the follow-up recorded below.

During final verification, the merge-script smoke test fetched a new official
tip, `6a8d34cd` (`exp-v0.52.548`, committed 2026-10-22T20:06:28Z). It adds trusted
proxy request-log hardening, so it was included rather than leaving the checkout
one revision behind. The final incoming range contains 3,498 commits.

The reviewed pending index was saved as the Git tree
`dff08738bcad44c3a1d53fe36ae18e59e1744029` (a tree object, not a commit). A
temporary Python refresh driver checked both refs, verified a clean worktree
against that index and the old tip's ancestry, aborted only this session's
pending merge, then invoked the existing no-commit Python merge helper against
the new tip. It restored the explicitly listed reviewed resolutions from the
backup tree and reapplied the exact official delta to the two overlapping
resolved files, `CHANGELOG.md` and `api/routes.py`, using `git apply --check
--index` before applying. Comparison against the backup showed exactly the 14
files in the new official delta; no fork resolution was lost. At the
pre-publication verification boundary, `MERGE_HEAD` and `upstream/master` both
resolved to `6a8d34cd`, with `HEAD` still at `014ae026`. The stale dry-run
checkpoint was cleared.

The user's running loopback llama server was treated as an existing service.
Validation uses fresh OS-assigned ports and disposable state, and never invokes
that model server or changes its configuration. Shutdowns address only the
specific WebUI processes spawned by this session's fixtures.

## Changed files and implementation

Upstream supplies the bulk of the staged changes. Six textual conflicts were
resolved: `CHANGELOG.md`, `start.ps1`, `static/boot.js`, `tests/test_insights.py`,
`tests/test_issue4982_openai_tts.py`, and `tests/test_updates.py`. Existing fork
changelog notes and official release text were retained without writing new
fork release entries. Tests retain both upstream additions and fork invariants.

`start.ps1` retains the official managed/source/runtime discovery and bare-source
fallback while preferring a valid `.venv` before legacy `venv`. The unchanged
fork wrapper still injects the configured password and supports `-Open`.

Irodori was updated to use `_beginTtsPlayback`, `_ownsTtsPlayback`,
`_stopActivePlaybackAudio`, `_sendTtsRequest`, and the current four-argument
`_playAudioBuf`. Its payload captures the original profile before any scheduler
delay or 429 retry. Voice mode shares the official lifecycle and rearm handling.
The engine is reserved against extension replacement. The backend includes
Irodori in the persisted server-engine selection, respects its own configured
voice rather than the Edge default, and uses the official no-proxy/no-redirect
opener with the bounded response buffer. README integration metadata and
workflow documentation were refreshed.

The official Python-discovery loop now supports the repository's Windows venv,
so the fork's duplicate local-venv probe was removed. The shared-key provider
implementation is already upstream-owned; the fork retains its behavioral
coverage rather than adding a second provider API.

Two Windows test-driver repairs keep the upstream assertions runnable:
`tests/test_ci_hygiene.py` uses the resolved Bash executable (bare `bash` can
select the unavailable WSL launcher even when Git Bash is installed), and
`tests/test_7860_model_provider_send_precedence.py` JSON-quotes the JavaScript
source path and writes its driver as UTF-8. The single real-filesystem update
test with a colon-containing filename is skipped only on Windows; its mocked
path-handling siblings and all valid Windows filename cases still run.

## Commands and verification evidence

All pytest commands use Git Bash to invoke `./scripts/test.sh`; the repository
`.venv` reports Python 3.12.10. Standalone Python tooling uses
`uv run --no-project --python .venv/Scripts/python.exe ...` unless explicitly
recorded as a diagnostic exception. No system test dependencies are installed.

Initial targeted baseline command:

```text
./scripts/test.sh tests/test_irodori_tts_engine.py tests/test_updates.py tests/test_update_channels.py tests/test_windows_native_launcher.py tests/test_windows_native_start.py tests/test_issue4982_openai_tts.py -q --timeout=60
```

Result: **160 passed**, 175.51 seconds. JUnit evidence is in disposable temporary
storage (`hermes-upstream-before.xml`).

The first post-merge attempts timed out in the shared server setup before any
regression assertion ran. The fixture discovered the neighboring real Agent
checkout, making startup slow and introducing optional dependency noise. Those
timeouts are not red regression evidence. Subsequent validation explicitly pins
the repository interpreter and a disposable, agent-free source marker, matching
the official credential-free CI mode; its WebUI server and all state remain
under a disposable temp namespace. Only the fixture-owned processes identified
from their temporary-state startup logs were stopped. An existing unrelated
WebUI process was not used for validation.

With that setup, the new Irodori regression selection produced **8 failed,
1 passed** (15.09 seconds) before the compatibility fixes: missing engine
fallback, wrong default voice, omitted profile, skipped cooldown, stale failure
clobbering, and stopped auto-read ownership. The profile-mismatch control already
passed. Separately the loopback-only transport regression failed **1 test**
(17.85 seconds) before the opener change: a redirect was followed and returned
200 rather than the required 502. Evidence: `hermes-upstream-red.xml` and
`hermes-upstream-transport-red.xml` in disposable temporary storage.

### Green and neighboring regression checks

The following groups overlap; their totals are not summed as a unique suite
count. JUnit filenames below are under the disposable `opencode` temp namespace.

| Verification | Actual result | Evidence |
| --- | --- | --- |
| Irodori, playback ownership/scheduler, OpenAI/Edge/ElevenLabs, settings, extension registry, Windows launchers | 164 passed, 1 skipped; 76.92 s | `hermes-upstream-tts-windows.xml` |
| Update channels/banner, providers/OpenCode, Insights, Agent source audit | Initial run: 421 passed, 5 skipped, 1 failed; failure was the Windows-invalid colon filename, not a product failure | `hermes-upstream-updates-providers.xml` |
| Complete updater module after the platform-specific fixture correction | 157 passed, 1 skipped; 203.41 s | `hermes-upstream-updates-green.xml` |
| OIDC/password/passkey/login limiter and Agent compatibility | 271 passed; 146.07 s | `hermes-upstream-security-compat.xml` |
| Regression, bootstrap/runtime discovery, CI runner, merge script, remote-image CSP/fallback | 145 passed, 1 skipped; 71.71 s | `hermes-upstream-regressions-green.xml` |
| Final exp-v0.52.548 logging/proxy tests, provider-send routing, login/OIDC, Irodori/playback and general regressions | 241 passed, 1 skipped; 79.51 s | `hermes-upstream-548-green.xml` |
| Isolated fork smoke script | All 4 checks passed: Irodori, shared OpenCode key, Windows wrapper, static hooks | `scripts/smoke_fork_features.py` |
| JS syntax | `node --check static/boot.js` and `node --check static/ui.js` passed | Terminal results |
| Pending-merge Ruff gate | 26 overlay Python files, 25 existing findings, 0 on session-authored adaptation lines | Temporary `lint_hermes_pending_merge.py` driver |
| Git validation | No unmerged paths, no fork deletions relative to the selected official tip, diff whitespace check passed | `git diff --check upstream/master`, merge ref checks |

The first broader Windows run reported 54 failures, 91 passes and 1 skip. Most
were locale-default CP932 decoding of UTF-8 source files; setting `PYTHONUTF8=1`
for the test process and its children fixed those without rewriting product
code. The remaining Bash-launch tests were repaired as described above. The
first final-tip run exposed 13 failures in the neighboring #7860 provider
driver because an unescaped Windows path produced an invalid JS Unicode escape;
its assertions now run unchanged through JSON-encoded paths, and the full
242-item final selection is green. These failures are retained as evidence,
not presented as passing runs.

The normal `scripts/ruff_lint.py --diff upstream/master` command also returned
success, but it compares committed `HEAD` with a merge base, so it is not proof
of a pending index. The additional temporary driver uses the repository's Ruff
configuration, JSON checker and diff-hunk parser against the actual working
tree; it normalizes Windows relative paths and intersects lines changed from
both merge parents to isolate this session's integration edits. It reports the
legacy findings separately and does not hide findings on new adaptation lines.

`npm run lint:runtime` could not execute because ESLint is not installed in this
checkout. No npm dependency was added for this check. JS syntax and real browser
initialization checks are independently green.

Representative exact test commands (Git Bash, isolated environment as above):

```text
./scripts/test.sh tests/test_irodori_tts_engine.py tests/test_openai_tts_chunk_generation_race.py tests/test_issue4982_openai_tts.py tests/test_issue7391_tts_default_engine.py tests/test_issue5435_tts_voice_preferences.py tests/test_issue2931_edge_tts_endpoint.py tests/test_issue3510_elevenlabs_tts.py tests/test_extension_tts_engine_registration.py tests/test_windows_native_launcher.py tests/test_windows_native_start.py tests/test_windows_native_support.py -q --timeout=180
./scripts/test.sh tests/test_auth_oidc.py tests/test_issue3825_oidc_auth.py tests/test_oidc_token_endpoint_auth.py tests/test_login_rate_limit_client_ip.py tests/test_passkey_auth.py tests/test_issue8126_passkey_malformed_input.py tests/test_agent_compat.py -q --timeout=180
./scripts/test.sh tests/test_regressions.py tests/test_bootstrap_python_selection.py tests/test_bootstrap_discover_agent.py tests/test_managed_runtime_startup.py tests/test_ci_hygiene.py tests/test_merge_official_updates_script.py tests/test_issue7941_csp_remote_image_exfiltration.py tests/test_issue7941_remote_image_fallback.py -q --timeout=180
./scripts/test.sh tests/test_786*.py tests/test_issue2775_log_request.py tests/test_login_rate_limit_client_ip.py tests/test_irodori_tts_engine.py tests/test_openai_tts_chunk_generation_race.py tests/test_auth_oidc.py tests/test_regressions.py -q --timeout=180
```

For the last command, PowerShell expanded the `test_786*.py` argument list from
`git ls-files` before calling the Bash runner. `--junitxml` pointed to the temp
evidence filenames listed above. No test dependencies went into system Python.
Direct `.venv/Scripts/python.exe -u -c ...` calls were limited to interpreter
and loopback connectivity diagnostics (Python SOP exception for diagnostics).

### Browser evidence and manual visual review

Used pinned Playwright 1.63.0 with headless Chromium 153.0.8010.12, fresh browser
contexts, minimal child environment, an agent-free runtime and a separate
loopback WebUI per checkout. The baseline was a disposable detached worktree of
`014ae026`; the final after pass ran the actual `exp-v0.52.548` integration. The
baseline worktree was removed after capture.

At 1440x1000, 720x900 and 390x844 (mobile/touch context), the real application
booted, opened Preferences, retained the Irodori/Hakua choices and 1.1x speed,
accepted keyboard voice selection, kept the picker inside the viewport with a
successful center hit-test, and returned the saved values after a hard reload.
All six before/after viewport cases recorded zero console/page errors. This
tests real UI/settings behavior; it is not a physical microphone or real audio
service test.

Screenshots and machine-readable results are ignored local review artifacts:

```text
.local-review/upstream-sync/before/{desktop,narrow,mobile}-{chat,irodori}.png
.local-review/upstream-sync/after/{desktop,narrow,mobile}-{chat,irodori}.png
.local-review/upstream-sync/{before,after}/results.json
```

Desktop, narrow and mobile images were read for visual review: the Irodori
controls remain visible, readable and contained; the updated mobile Preferences
and chat shell preserve the native fork controls. The refreshed upstream locale
also supplies the Japanese labels seen in the after capture.

## Primary sources checked

Checked on 2026-10-23; repository API timestamps use UTC.

- Final official source revision: https://github.com/nesquena/hermes-webui/commit/6a8d34cd4974cec0c23632c8d1d3168fdee380cd
- Initial integration revision: https://github.com/nesquena/hermes-webui/commit/74d7c11da7e8f3a6774be43f81c0e2687ea6eef9
- Official stable release: https://github.com/nesquena/hermes-webui/releases/tag/v0.52.492
- The official repository security-advisories API and GitHub's reviewed advisory
  query for `hermes-webui` returned no entries. This is not evidence of absence
  of vulnerabilities; maintenance claims refer to the actual merged official
  code/changelog, not an invented CVE or independent full security audit.
- Temporary browser verification tooling: Microsoft Playwright Python's official
  repository and PyPI metadata were checked. Pinned `playwright==1.63.0`
  (Windows wheel uploaded 2026-09-15) is used through an isolated `uv --with`
  environment rather than changing project dependencies. The reviewed advisory
  https://github.com/advisories/GHSA-7mvr-c777-76hp lists the older npm browser
  download issue as fixed in 1.55.1; no project package-trust certification is
  implied by this limited verification-tool check.

## Self-review

Self-review-event: qa_defect. The initial post-merge server-setup timeouts were
investigated rather than counted as bug reproduction. The existing narrow
isolation mechanism was made explicit in the validation environment; regression
assertions were then run before fixes. Governance changes are unnecessary:
project instructions already require isolated, credential-free verification.
The self-review skill was read and applied in review-only mode.

Self-review-event: ticket_completed. The final review checked the requested
fork surfaces, every conflict, the late official-tip delta, current merge refs,
red/green evidence, and desktop/narrow/mobile artifacts. Two further QA gaps
were addressed: the branch-only lint gate was supplemented with a pending-tree
check, and the Windows-only test harness failures were corrected without
weakening their product assertions. Rejected broader changes: automatic
AGENTS/skill/SOP edits and unrelated legacy lint cleanup; the existing rules
already describe the needed isolation and evidence controls.

## Residual risks and recommended next actions

The repository-wide suite and ESLint runtime guard were not completed; the
affected and neighboring groups above passed. External Irodori synthesis,
physical microphone/audio output, real provider credentials, live Agent chat,
Docker and production startup were not exercised. Those are the remaining
operational verification boundaries, not known regressions. The user's llama
server and existing WebUI runtime were kept outside the test boundary.

The complete resolved merge includes official security maintenance. Production
adoption and paired Agent-version compatibility remain checks for the
operator's normal deployment process. The recorded backup Git tree is an
earlier safety snapshot, not a substitute for the final reviewed integration.

## Publication follow-up

On 2026-10-23 the user explicitly requested committing and pushing `master`.
This section records the authorisation and pre-publication evidence, without
predicting a successful push or CI result.

Preflight inspected `git status`, staged/unstaged diffs, the last ten commits,
merge parents, update remote and GitHub authentication. `git fetch origin master`
confirmed that `origin/master` still points to `014ae026`; the selected official
parent is `6a8d34cd`. All 1,048 staged files belong to the reviewed integration.
No unstaged tracked changes or unresolved conflicts were present. Only the two
pre-existing `.cursor/` files remain untracked. The sensitive-file-name check
finds only the intentional `.env.example` and `.env.docker.example` templates;
no real environment, key, auth or local review artifact is staged. The staged
diff whitespace check against the official parent passes.

Selected publication commands:

```text
git commit -m "Merge official Hermes WebUI exp-v0.52.548"
git push origin master
```

The resulting commit and its parents are authoritative in Git, and the remote
SHA and CI outcomes are checked through GitHub after the push. Existing
verification above applies to the unchanged code; this follow-up only updates
the publication record. The running llama server remains outside the operation.
