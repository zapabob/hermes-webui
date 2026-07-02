#!/usr/bin/env python3
"""Fetch and merge the official Hermes WebUI upstream.

Strategy
--------
Uses a normal ``git merge`` (not rebase) so fork-only commits stay on the branch
history and Git remains the source of truth for conflict resolution. The script:

1. Records a JSON checkpoint before/after each phase (power-loss recovery).
2. Fetches the official branch into a namespaced remote-tracking ref.
3. Summarises local-only vs upstream-only commits.
4. Previews conflicts via ``git merge-tree``.
5. Runs ``git merge --no-edit`` unless ``--dry-run``.

Known fork paths that often need manual attention after a merge are listed in
``FORK_PRESERVE_HINTS`` and printed when conflicts touch them.

Windows: run with ``py -3 scripts/merge_official_updates.py`` from PowerShell.
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DEFAULT_OFFICIAL_URL = "https://github.com/nesquena/hermes-webui.git"
CHECKPOINT_NAME = ".hermes-webui-merge-checkpoint.json"
CHECKPOINT_VERSION = 1

# Fork-only surfaces — keep local behaviour; align to official APIs when both change.
FORK_PRESERVE_HINTS: dict[str, str] = {
    "CHANGELOG.md": (
        "Keep the fork [Unreleased] section at the top, then append official "
        "release entries from upstream. Do not drop Irodori/OpenCode/Windows notes."
    ),
    "CONTRIBUTORS.md": (
        "Union upstream contributor credits with any fork-specific entries."
    ),
    "README.md": (
        "Preserve the 'Local fork highlights' section; update the tracked upstream "
        "version string to the latest official tag."
    ),
    "api/config.py": (
        "Keep OPENCODE_API_KEY shared detection alongside official per-provider keys."
    ),
    "api/providers.py": (
        "Keep OPENCODE_API_KEY enabling both opencode-zen and opencode-go."
    ),
    "api/routes.py": (
        "Preserve Irodori TTS helpers and /api/tts irodori engine handling; "
        "adopt upstream TTS/prosody changes around them."
    ),
    "api/updates.py": (
        "Keep fork update-check logic that ignores upstream-only tags missing "
        "from the configured update remote."
    ),
    "static/ui.js": (
        "Preserve Irodori TTS client paths (_irodoriTtsPayload, engine==='irodori')."
    ),
    "static/boot.js": (
        "Preserve Irodori voice-mode boot paths."
    ),
    "scripts/windows/start-hermes-webui-native.ps1": (
        "Keep password injection and -Open browser launch; adopt upstream start.ps1 "
        "delegation changes underneath."
    ),
    "scripts/merge_official_updates.py": (
        "This script — prefer local enhancements when merging."
    ),
}


@dataclass
class MergeCheckpoint:
    version: int = CHECKPOINT_VERSION
    phase: str = "init"
    started_at: str = ""
    updated_at: str = ""
    repo: str = ""
    official_url: str = DEFAULT_OFFICIAL_URL
    remote_name: str = "official"
    official_ref: str = "master"
    target_name: str = ""
    local_head: str = ""
    upstream_head: str = ""
    upstream_tag: str = ""
    merge_base: str = ""
    dry_run: bool = False
    conflict_files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def touch(self, phase: str, **extra: Any) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.started_at:
            self.started_at = now
        self.updated_at = now
        self.phase = phase
        for key, value in extra.items():
            setattr(self, key, value)


def _try_import_tqdm() -> Callable[..., Any] | None:
    try:
        from tqdm import tqdm  # type: ignore[import-not-found]

        return tqdm
    except ImportError:
        return None


class Progress:
    """tqdm wrapper with a no-op fallback."""

    def __init__(self, total: int, desc: str) -> None:
        self._tqdm_factory = _try_import_tqdm()
        self._bar: Any = None
        if self._tqdm_factory is not None:
            self._bar = self._tqdm_factory(total=total, desc=desc, unit="step", leave=False)
        else:
            print(f"{desc}...", flush=True)
        self._fallback_total = total
        self._fallback_current = 0

    def update(self, n: int = 1) -> None:
        if self._bar is not None:
            self._bar.update(n)
        else:
            self._fallback_current += n

    def close(self) -> None:
        if self._bar is not None:
            self._bar.close()


def configure_stdio() -> None:
    """Prefer UTF-8 console output on Windows hosts with legacy code pages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def run_git(args: list[str], repo: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def git_text(args: list[str], repo: Path, check: bool = True) -> str:
    return run_git(args, repo, check=check).stdout.strip()


def is_shallow_repository(repo: Path) -> bool:
    status = git_text(["rev-parse", "--is-shallow-repository"], repo, check=False)
    return status.strip().lower() == "true"


def merge_base(repo: Path, target_name: str) -> str:
    base = run_git(["merge-base", "HEAD", target_name], repo, check=False)
    if base.returncode == 0:
        return base.stdout.strip()
    if is_shallow_repository(repo):
        print("Local checkout is shallow; fetching origin history before merge-base.")
        run_git(["fetch", "--unshallow", "origin"], repo, check=False)
        base = run_git(["merge-base", "HEAD", target_name], repo, check=False)
        if base.returncode == 0:
            return base.stdout.strip()
    raise subprocess.CalledProcessError(base.returncode, base.args, output=base.stdout, stderr=base.stderr)


def ensure_repo(path: Path) -> Path:
    root = git_text(["rev-parse", "--show-toplevel"], path)
    return Path(root)


def checkpoint_path(repo: Path) -> Path:
    return repo / CHECKPOINT_NAME


def load_checkpoint(repo: Path) -> MergeCheckpoint | None:
    path = checkpoint_path(repo)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return MergeCheckpoint(**data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def save_checkpoint(repo: Path, checkpoint: MergeCheckpoint) -> None:
    path = checkpoint_path(repo)
    path.write_text(json.dumps(asdict(checkpoint), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clear_checkpoint(repo: Path) -> None:
    path = checkpoint_path(repo)
    if path.is_file():
        path.unlink()


def tracked_changes(repo: Path) -> str:
    return git_text(["status", "--porcelain", "--untracked-files=no"], repo)


def is_merge_in_progress(repo: Path) -> bool:
    return (repo / ".git" / "MERGE_HEAD").is_file()


def latest_tag(repo: Path, ref: str) -> str:
    tag = git_text(["describe", "--tags", "--abbrev=0", ref], repo, check=False)
    return tag or "unknown"


def short_log(repo: Path, rev_range: str, limit: int) -> str:
    return git_text(["log", "--oneline", f"--max-count={limit}", rev_range], repo, check=False)


def remote_exists(repo: Path, name: str) -> bool:
    remotes = git_text(["remote"], repo, check=False)
    return name in {line.strip() for line in remotes.splitlines() if line.strip()}


def ensure_remote(repo: Path, name: str, url: str) -> None:
    if remote_exists(repo, name):
        current = git_text(["remote", "get-url", name], repo, check=False)
        if current and current != url:
            print(f"Note: remote '{name}' URL is {current!r} (expected {url!r}). Using existing remote.")
        return
    print(f"Adding git remote '{name}' -> {url}")
    print(run_git(["remote", "add", name, url], repo).stdout.rstrip())


def parse_conflict_files(merge_tree_output: str) -> list[str]:
    conflicts: list[str] = []
    for line in merge_tree_output.splitlines():
        if "CONFLICT" in line and "Merge conflict in" in line:
            marker = "Merge conflict in "
            idx = line.find(marker)
            if idx >= 0:
                conflicts.append(line[idx + len(marker) :].strip())
    # merge-tree also emits "CONFLICT (content): Merge conflict in FILE"
    if not conflicts:
        for line in merge_tree_output.splitlines():
            if "Merge conflict in " in line:
                conflicts.append(line.split("Merge conflict in ", 1)[1].strip())
    return sorted(set(conflicts))


def print_conflict_guidance(conflict_files: list[str]) -> None:
    if not conflict_files:
        return
    print("\nConflict resolution guidance for known fork paths:")
    for path in conflict_files:
        hint = FORK_PRESERVE_HINTS.get(path.replace("\\", "/"))
        if hint:
            print(f"  - {path}: {hint}")
        else:
            print(f"  - {path}: resolve manually; prefer upstream for core API, local for fork-only features.")
    untouched = sorted(set(FORK_PRESERVE_HINTS) - {p.replace("\\", "/") for p in conflict_files})
    if untouched:
        print("\nFork paths that auto-merged (verify behaviour after merge):")
        for path in untouched[:12]:
            print(f"  - {path}: {FORK_PRESERVE_HINTS[path]}")
        if len(untouched) > 12:
            print(f"  ... and {len(untouched) - 12} more listed in FORK_PRESERVE_HINTS")


def install_signal_handlers(repo: Path, checkpoint: MergeCheckpoint) -> None:
    def _handler(signum: int, _frame: Any) -> None:
        checkpoint.notes.append(f"Interrupted by signal {signum} during phase {checkpoint.phase}")
        save_checkpoint(repo, checkpoint)
        print("\nCheckpoint saved. Re-run with --resume after resolving the interruption.")
        raise SystemExit(130)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _handler)  # type: ignore[attr-defined]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-url", default=DEFAULT_OFFICIAL_URL)
    parser.add_argument("--official-ref", default="master")
    parser.add_argument(
        "--remote-name",
        default="",
        help="Remote to fetch into (default: use existing 'upstream', else 'official').",
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-tracked-changes",
        action="store_true",
        help="Allow merge even when tracked files already have local modifications.",
    )
    parser.add_argument("--log-limit", type=int, default=24)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint or an in-progress git merge (skip fetch/preview).",
    )
    parser.add_argument(
        "--abort",
        action="store_true",
        help="Abort an in-progress merge and remove the checkpoint file.",
    )
    parser.add_argument(
        "--clear-checkpoint",
        action="store_true",
        help="Delete the checkpoint file without merging.",
    )
    return parser.parse_args()


def resolve_remote_name(repo: Path, requested: str) -> str:
    if requested:
        return requested
    if remote_exists(repo, "upstream"):
        return "upstream"
    if remote_exists(repo, "official"):
        return "official"
    return "official"


def main() -> int:
    args = parse_args()
    repo = ensure_repo(Path(args.repo).resolve())
    remote_name = resolve_remote_name(repo, args.remote_name.strip())
    target_ref = f"refs/remotes/{remote_name}/{args.official_ref}"
    target_name = f"{remote_name}/{args.official_ref}"

    if args.clear_checkpoint:
        clear_checkpoint(repo)
        print("Checkpoint cleared.")
        return 0

    if args.abort:
        if is_merge_in_progress(repo):
            print(run_git(["merge", "--abort"], repo, check=False).stdout.rstrip())
        clear_checkpoint(repo)
        print("Merge aborted and checkpoint cleared.")
        return 0

    checkpoint = load_checkpoint(repo) or MergeCheckpoint(
        repo=str(repo),
        official_url=args.official_url,
        remote_name=remote_name,
        official_ref=args.official_ref,
        target_name=target_name,
        dry_run=args.dry_run,
    )
    install_signal_handlers(repo, checkpoint)

    dirty = tracked_changes(repo)
    if dirty and not args.allow_tracked_changes and not args.resume:
        print("Refusing to merge with tracked local modifications:")
        print(dirty)
        print("Re-run with --allow-tracked-changes only if those changes are intentional.")
        return 2

    progress = Progress(total=5 if not args.resume else 2, desc="Upstream merge")
    try:
        if args.resume and is_merge_in_progress(repo):
            checkpoint.touch("merging", notes=checkpoint.notes + ["Resuming in-progress git merge"])
            save_checkpoint(repo, checkpoint)
            progress.update()
            print("Resuming in-progress merge (MERGE_HEAD present)...")
        elif not args.resume:
            checkpoint.touch("fetch")
            save_checkpoint(repo, checkpoint)
            progress.update()

            print(f"Repository: {repo}")
            ensure_remote(repo, remote_name, args.official_url)
            print(f"Fetching official upstream: {args.official_url} {args.official_ref} -> {target_name}")
            fetch_refspec = f"{args.official_ref}:{target_ref}"
            fetch_output = run_git(["fetch", remote_name, fetch_refspec, "--tags"], repo, check=False)
            if fetch_output.returncode and remote_name == "official" and not remote_exists(repo, remote_name):
                # First run without remote: fetch by URL into namespaced ref.
                fetch_output = run_git(["fetch", args.official_url, fetch_refspec, "--tags"], repo, check=False)
            print(fetch_output.stdout.rstrip())
            if fetch_output.returncode:
                checkpoint.notes.append("Fetch failed")
                save_checkpoint(repo, checkpoint)
                return fetch_output.returncode

            checkpoint.touch("fetched")
            save_checkpoint(repo, checkpoint)
            progress.update()

            head = git_text(["rev-parse", "--short", "HEAD"], repo)
            upstream = git_text(["rev-parse", "--short", target_name], repo)
            base = merge_base(repo, target_name)
            official_tag = latest_tag(repo, target_name)
            checkpoint.touch(
                "preview",
                local_head=head,
                upstream_head=upstream,
                upstream_tag=official_tag,
                merge_base=base[:12],
            )
            save_checkpoint(repo, checkpoint)
            progress.update()

            print(f"Local HEAD: {head}")
            print(f"Official {target_name}: {upstream} ({official_tag})")
            print(f"Merge base: {base[:12]}")

            local_only = short_log(repo, f"{target_name}..HEAD", args.log_limit)
            official_only = short_log(repo, f"HEAD..{target_name}", args.log_limit)
            print("\nLocal-only commits to preserve:")
            print(local_only or "  none")
            print("\nOfficial commits to bring in:")
            print(official_only or "  none")

            preview = run_git(["merge-tree", "--write-tree", "HEAD", target_name], repo, check=False)
            conflict_files = parse_conflict_files(preview.stdout)
            checkpoint.conflict_files = conflict_files
            if preview.returncode:
                print("\nMerge preview reports conflicts. Running git merge will stop for resolution.")
                print(preview.stdout.rstrip())
                print_conflict_guidance(conflict_files)
            else:
                print("\nMerge preview is clean.")
            checkpoint.touch("previewed", conflict_files=conflict_files)
            save_checkpoint(repo, checkpoint)
            progress.update()

            if args.dry_run:
                print("\nDry run complete; no merge performed.")
                print(f"Checkpoint: {checkpoint_path(repo)}")
                return 0

            if head == upstream:
                print("\nAlready up to date with official upstream.")
                clear_checkpoint(repo)
                return 0

        checkpoint.touch("merging")
        save_checkpoint(repo, checkpoint)
        progress.update()

        print(f"\nMerging {target_name} into current branch...")
        merge = run_git(["merge", "--no-edit", target_name], repo, check=False)
        print(merge.stdout.rstrip())
        if merge.returncode:
            conflicts = git_text(["diff", "--name-only", "--diff-filter=U"], repo, check=False)
            conflict_files = [line for line in conflicts.splitlines() if line.strip()]
            checkpoint.touch("conflicts", conflict_files=conflict_files)
            checkpoint.notes.append("Merge stopped for manual conflict resolution")
            save_checkpoint(repo, checkpoint)
            print_conflict_guidance(conflict_files)
            print("\nMerge stopped with conflicts. Resolve them, then run `git commit --no-edit`.")
            print(f"Checkpoint: {checkpoint_path(repo)}")
            print("After committing, run with --clear-checkpoint or re-run merge script to refresh.")
            return merge.returncode

        checkpoint.touch("completed")
        save_checkpoint(repo, checkpoint)
        progress.update()
        clear_checkpoint(repo)
        print("\nMerge completed.")
        return 0
    finally:
        progress.close()


if __name__ == "__main__":
    configure_stdio()
    sys.exit(main())
