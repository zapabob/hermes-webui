# 2026-07-24 Upstream merge + red-team campaign (Cursor)

## Overview

Created the reusable skill `hermes-webui-upstream-redteam`, merged official `upstream/master` into fork `master` while preserving fork surfaces, fixed CI mock breakage from the hybrid update-check API, and opened the first upstream hardening PR toward the campaign goal of 15 completed items.

## Background / requirements

- Sync official features/fixes via `scripts/merge_official_updates.py` (direct `git merge` used after dry-run hung on disk pressure / merge-tree cost).
- Preserve fork: Irodori TTS, OPENCODE shared key, Windows launcher, remote-tag update gating, merge script.
- Red-team official tip for unresolved / non-duplicate CVE-class issues; PR in King's English; harden agent boundaries without removing capability.
- Goal = continue until 15 completions.

## Assumptions / decisions

- Disk was ~3–4GB free; avoided expensive `merge-tree` preview; cleaned temp packs.
- #6126 TOCTOU race is maintainer-reserved — do not compete.
- #6424 → opt-in strict registration (maintainer-recommended shape), not default containment.

## Changed files (high level)

- Skill: `~/.cursor/skills/hermes-webui-upstream-redteam/SKILL.md` (+ project mirror under `.cursor/skills/`)
- Merge on `master`: upstream tip through collapsed wakeup cards (`bf148fd2` + changelog `fdc55d3b`)
- CI fix: `tests/test_updates.py`, `tests/test_update_channels.py` (`ac45f945`)
- Upstream PR branch: `api/workspace.py`, `.env.example`, tests, CHANGELOG → https://github.com/nesquena/hermes-webui/pull/6470

## Commands run

- `git fetch upstream master` / `git merge --no-edit upstream/master`
- Conflict resolution (hybrid for `api/updates.py`)
- `git push origin master`
- `gh pr create` → #6470
- `gh workflow run "Docker smoke"` (path-filtered; not triggered by test-only fix)

## Test / verification results

- Fork `Tests` + `Browser smoke` **success** on `ac45f945`
- Prior merge push: Docker smoke **failed** (three-container: hermes-agent requirements install / dashboard auth refuse bind) — re-dispatched workflow `30066051604`
- Strict registration smoke (direct Python, not full pytest session): reject/home/default paths OK

## Campaign counter

See `_docs/redteam-campaign-counter.md` — **2/15** tracked (merge + PR #6470), pending Docker green for merge item.

## Residual risk

- Full 15 PRs not completed this session; continue from skill + counter.
- Docker smoke may still fail for upstream agent/dashboard reasons unrelated to fork merge.
- Fork update tests are signature-compatible but may need stronger assertions if channel probes expand.

## Next recommended actions

1. Wait for Docker smoke `30066051604`; if still red, triage vs upstream three-container expectations.
2. Next red-team candidates (skip duplicates): env/secret redaction gaps, agent tool path escapes not covered by `safe_resolve_ws` / `open_anchored_fd`, subprocess argv hardening.
3. Keep iterating until counter ≥ 15.
