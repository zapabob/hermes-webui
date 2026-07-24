# Red-team campaign counter

**Goal:** 15 completed items (fork merge CI-green counts as 1; each non-duplicate upstream PR counts as 1).

| # | Date | Type | Title / URL | Status |
|---|------|------|-------------|--------|
| 1 | 2026-07-24 | fork-merge | Merge `upstream/master` → `master` (`bf148fd2` / `fdc55d3b` / CI fix `ac45f945`) | Tests+Browser green; Docker smoke re-run `30066051604` |
| 2 | 2026-07-24 | upstream-pr | Opt-in strict workspace registration (#6424) — https://github.com/nesquena/hermes-webui/pull/6470 | opened |

## In progress findings

- #6126 public-share TOCTOU — **blocked** (maintainer self-reserved)
- #6424 default containment — **rejected as product policy**; shipped opt-in instead (#6470)

## Blocked / not counted

- Competing on #6126 race after maintainer reservation
