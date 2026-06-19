#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, args, proc.stdout, proc.stderr)
    return proc


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], check=check)


def require_branch(ref: str) -> None:
    proc = git("rev-parse", "--verify", ref, check=False)
    if proc.returncode:
        raise SystemExit(f"Missing git ref: {ref}")


def status_porcelain() -> list[str]:
    proc = git("status", "--porcelain", check=True)
    return [line for line in proc.stdout.splitlines() if line]


def print_section(title: str, body: str) -> None:
    print(f"\n== {title} ==")
    print(body.rstrip() or "(none)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge an official upstream branch while preserving fork-owned work."
    )
    parser.add_argument("--upstream", default="upstream/master", help="official branch to merge")
    parser.add_argument("--base", default="HEAD", help="local branch/ref to compare")
    parser.add_argument("--skip-fetch", action="store_true", help="do not fetch remotes first")
    parser.add_argument("--allow-dirty", action="store_true", help="allow existing worktree changes")
    parser.add_argument("--merge", action="store_true", help="run git merge --no-commit")
    args = parser.parse_args()

    if not args.skip_fetch:
        git("fetch", "--all", "--prune", "--tags")

    require_branch(args.base)
    require_branch(args.upstream)

    dirty = status_porcelain()
    if dirty and not args.allow_dirty:
        print_section("Dirty worktree", "\n".join(dirty))
        raise SystemExit("Refusing to merge with existing changes. Re-run with --allow-dirty if intentional.")

    counts = git("rev-list", "--left-right", "--count", f"{args.base}...{args.upstream}").stdout.strip()
    print_section("Ahead/behind", f"{args.base}...{args.upstream}: {counts}")

    upstream_log = git("log", "--oneline", "--decorate", f"{args.base}..{args.upstream}", "-n", "40").stdout
    print_section("Incoming official commits", upstream_log)

    local_files = git("diff", "--name-status", f"{args.upstream}...{args.base}").stdout
    print_section("Fork overlay files", local_files)

    if not args.merge:
        print("\nDry run only. Pass --merge to run git merge --no-commit.")
        return 0

    merge = git("merge", "--no-ff", "--no-commit", args.upstream, check=False)
    if merge.stdout:
        print(merge.stdout, end="")
    if merge.stderr:
        print(merge.stderr, end="", file=sys.stderr)

    conflicts = git("diff", "--name-only", "--diff-filter=U", check=False).stdout.strip()
    if merge.returncode:
        print_section("Merge conflicts", conflicts)
        return merge.returncode

    print_section("Merge result", "Merged cleanly and left changes staged/unstaged for review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
