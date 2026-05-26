#!/usr/bin/env python3
"""Fetch and merge the official Hermes WebUI upstream.

The script is intentionally small: it records the local/official commit
shape, fetches the official branch into a namespaced remote-tracking ref, and
then runs a normal git merge so Git remains the source of truth for conflict
handling.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_OFFICIAL_URL = "https://github.com/nesquena/hermes-webui.git"


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


def ensure_repo(path: Path) -> Path:
    root = git_text(["rev-parse", "--show-toplevel"], path)
    return Path(root)


def tracked_changes(repo: Path) -> str:
    return git_text(["status", "--porcelain", "--untracked-files=no"], repo)


def latest_tag(repo: Path, ref: str) -> str:
    tag = git_text(["describe", "--tags", "--abbrev=0", ref], repo, check=False)
    return tag or "unknown"


def short_log(repo: Path, rev_range: str, limit: int) -> str:
    return git_text(["log", "--oneline", f"--max-count={limit}", rev_range], repo, check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-url", default=DEFAULT_OFFICIAL_URL)
    parser.add_argument("--official-ref", default="master")
    parser.add_argument("--remote-name", default="official")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-tracked-changes",
        action="store_true",
        help="Allow merge even when tracked files already have local modifications.",
    )
    parser.add_argument("--log-limit", type=int, default=24)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = ensure_repo(Path(args.repo).resolve())
    target_ref = f"refs/remotes/{args.remote_name}/{args.official_ref}"
    target_name = f"{args.remote_name}/{args.official_ref}"

    dirty = tracked_changes(repo)
    if dirty and not args.allow_tracked_changes:
        print("Refusing to merge with tracked local modifications:")
        print(dirty)
        print("Re-run with --allow-tracked-changes only if those changes are intentional.")
        return 2

    print(f"Repository: {repo}")
    print(f"Fetching official upstream: {args.official_url} {args.official_ref} -> {target_name}")
    fetch_refspec = f"{args.official_ref}:{target_ref}"
    print(run_git(["fetch", args.official_url, fetch_refspec, "--tags"], repo).stdout.rstrip())

    head = git_text(["rev-parse", "--short", "HEAD"], repo)
    upstream = git_text(["rev-parse", "--short", target_name], repo)
    base = git_text(["merge-base", "HEAD", target_name], repo)
    official_tag = latest_tag(repo, target_name)
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
    if preview.returncode:
        print("\nMerge preview reports conflicts. Running git merge will stop for resolution.")
        print(preview.stdout.rstrip())
    else:
        print("\nMerge preview is clean.")

    if args.dry_run:
        print("\nDry run complete; no merge performed.")
        return 0

    print(f"\nMerging {target_name} into current branch...")
    merge = run_git(["merge", "--no-edit", target_name], repo, check=False)
    print(merge.stdout.rstrip())
    if merge.returncode:
        print("\nMerge stopped with conflicts. Resolve them, then run `git commit --no-edit`.")
        return merge.returncode

    print("\nMerge completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
